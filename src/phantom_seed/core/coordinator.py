"""GameCoordinator — orchestrates AI generation, state, and game flow."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from phantom_seed.ai.chains import CharacterChain, SceneChain
from phantom_seed.ai.imagen_client import ImagenClient
from phantom_seed.ai.protocol import (
    FALLBACK_SCENE,
    CharacterProfile,
    Choice,
    Position,
    SceneData,
    StageAction,
    StageCommand,
    VisualType,
)
from phantom_seed.core.roguelike import generate_memory_fragment, roll_random_event
from phantom_seed.core.seed_engine import (
    derive_initial_atmosphere,
    derive_trait_code,
    hash_seed,
)
from phantom_seed.core.state import GameState

if TYPE_CHECKING:
    from phantom_seed.config import Config

log = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]


class GameCoordinator:
    """Central coordinator that drives the game loop."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.character_chain = CharacterChain(config)
        self.scene_chain = SceneChain(config)
        self.imagen = ImagenClient(config)
        self.state = GameState(
            affection=config.initial_affection,
        )
        self.heroines: list[CharacterProfile] = []
        self.heroine_sprite_paths: dict[str, Path] = {}
        self.character: CharacterProfile | None = None
        self.seed_hash: str = ""
        self.atmosphere: str = ""
        self.current_scene: SceneData | None = None
        self.character_sprite_path: Path | None = None
        # Background description → generated image path (reuse across scenes)
        self._bg_cache: dict[str, str] = {}
        self._bg_lock = threading.Lock()

    def _heroine_variants(self, seed_string: str) -> list[tuple[str, str]]:
        variants: list[tuple[str, str]] = []
        for idx in range(3):
            variant_hash = hash_seed(f"{seed_string}:heroine:{idx}")
            variants.append((variant_hash, derive_trait_code(variant_hash)))
        return variants

    def _fallback_heroine(self, index: int) -> CharacterProfile:
        fallback_names = ["朝雾 澪", "七濑 诗织", "久远 纱夜"]
        fallback_hair = ["long silver hair", "wavy chestnut hair", "short black bob hair"]
        fallback_eyes = ["violet eyes", "amber eyes", "emerald eyes"]
        fallback_styles = [
            "soft knit cardigan and long skirt",
            "smart casual blouse and fitted slacks",
            "layered monochrome jacket and pleated skirt",
        ]
        return CharacterProfile(
            name=fallback_names[index % len(fallback_names)],
            personality="外表沉着克制。熟悉之后会露出温柔而有些笨拙的一面。她有很强的行动力，也藏着不愿轻易示人的脆弱。",
            speech_pattern="说话简洁，但会在关键时刻补上一句非常真诚的话。情绪波动时会故作平静。熟人面前偶尔会露出一点带笑的吐槽语气。",
            visual_description=(
                "an attractive adult university student woman, "
                f"{fallback_hair[index % len(fallback_hair)]}, "
                f"{fallback_eyes[index % len(fallback_eyes)]}, "
                f"{fallback_styles[index % len(fallback_styles)]}, "
                "distinctive accessory, elegant anime visual novel style"
            ),
            signature_look=(
                f"{fallback_hair[index % len(fallback_hair)]} with "
                f"{fallback_eyes[index % len(fallback_eyes)]}"
            ),
            backstory="她在校园里看上去总是很从容，但其实一直背负着未说出口的压力。正因如此，她格外珍惜真正理解自己的人。",
            secrets=["有不愿被别人发现的兴趣", "紧张时会下意识摸自己的配饰", "对亲近的人非常护短"],
            relationship_to_player="起初只是偶然结识，但在一次次共同经历中逐渐发展出不同寻常的羁绊。",
        )

    def _generate_heroines(self, seed_string: str) -> None:
        self.heroines.clear()
        self.heroine_sprite_paths.clear()
        for idx, (seed_hash, trait_code) in enumerate(self._heroine_variants(seed_string)):
            try:
                heroine = self.character_chain.invoke(seed_hash, trait_code)
            except Exception:
                log.exception("Failed to generate heroine %s", idx)
                heroine = self._fallback_heroine(idx)
            self.heroines.append(heroine)
            self.state.register_heroine(heroine.name, initial_affection=self.config.initial_affection)

    def _generate_single_heroine(
        self,
        idx: int,
        seed_hash: str,
        trait_code: str,
    ) -> CharacterProfile:
        try:
            return self.character_chain.invoke(seed_hash, trait_code)
        except Exception:
            log.exception("Failed to generate heroine %s", idx)
            return self._fallback_heroine(idx)

    def _generate_single_sprite(self, heroine: CharacterProfile) -> tuple[str, Path | None]:
        try:
            return heroine.name, self.imagen.generate_character_sprite(heroine.visual_description)
        except Exception:
            log.exception("Failed to generate heroine sprite: %s", heroine.name)
            return heroine.name, None

    def _cast_summary(self) -> str:
        if not self.heroines:
            return "暂无女主阵容。"
        chunks = []
        for heroine in self.heroines:
            score = self.state.heroine_score(heroine.name)
            chunks.append(
                "\n".join(
                    [
                        f"- {heroine.name}",
                        f"  - 当前好感: {score}",
                        f"  - 性格: {heroine.personality}",
                        f"  - 说话方式: {heroine.speech_pattern}",
                        f"  - 视觉锚点: {heroine.signature_look or heroine.visual_description[:80]}",
                        f"  - 初始关系: {heroine.relationship_to_player}",
                    ]
                )
            )
        return "\n".join(chunks)

    def _pick_focus_heroine(self) -> CharacterProfile | None:
        if not self.heroines:
            return None
        self.state.update_route_state()
        target_name = self.state.route_locked_to or self.state.active_heroine
        if not target_name and self.state.ranked_heroines():
            target_name = self.state.ranked_heroines()[0][0]
        if not target_name:
            target_name = self.heroines[min(self.state.round_number % len(self.heroines), len(self.heroines) - 1)].name
        for heroine in self.heroines:
            if heroine.name == target_name:
                self.state.set_active_heroine(heroine.name)
                self.character = heroine
                self.character_sprite_path = self.heroine_sprite_paths.get(heroine.name)
                return heroine
        heroine = self.heroines[0]
        self.state.set_active_heroine(heroine.name)
        self.character = heroine
        self.character_sprite_path = self.heroine_sprite_paths.get(heroine.name)
        return heroine

    def heroine_sprite_items(self) -> list[tuple[str, Path]]:
        return list(self.heroine_sprite_paths.items())

    def _heroine_names(self) -> list[str]:
        return [heroine.name for heroine in self.heroines]

    def _ending_target(self) -> str:
        heroine_name = self.state.route_locked_to or self.state.active_heroine
        if not heroine_name:
            return "暂未决定结局等级。"
        grade = self.state.ending_grade(heroine_name)
        return f"{heroine_name} 线路目标结局：{grade}"

    def _normalize_choices(self, scene: SceneData) -> None:
        heroine_names = self._heroine_names()
        if not scene.choices:
            focus_name = self.state.route_locked_to or self.state.active_heroine
            if not focus_name and heroine_names:
                focus_name = heroine_names[0]
            if focus_name:
                scene.choices = [
                    Choice(
                        text=f"靠近{focus_name}",
                        target_state_delta={
                            "affection": 3,
                            f"heroine:{focus_name}": 5,
                        },
                    ),
                    Choice(
                        text="暂时保持距离",
                        target_state_delta={"affection": 0},
                    ),
                ]
        if not scene.choices:
            return

        if self.state.route_phase == "lock_window" and heroine_names:
            for idx, choice in enumerate(scene.choices[: len(heroine_names)]):
                delta = choice.target_state_delta
                if not any(key.startswith("heroine:") for key in delta):
                    heroine_name = heroine_names[idx % len(heroine_names)]
                    delta[f"heroine:{heroine_name}"] = max(4, delta.get("affection", 2))
        elif self.state.route_locked_to:
            locked = self.state.route_locked_to
            for choice in scene.choices:
                delta = choice.target_state_delta
                if "affection" in delta and f"heroine:{locked}" not in delta:
                    delta[f"heroine:{locked}"] = delta["affection"]

    def _postprocess_scene(self, scene: SceneData) -> SceneData:
        self._normalize_choices(scene)
        self._normalize_stage_blocking(scene)
        if self.state.route_phase in ("climax", "ending"):
            scene.game_state_update.is_climax = True
        if self.state.route_phase == "ending":
            scene.game_state_update.is_ending = True
            locked = self.state.route_locked_to or self.state.active_heroine
            ending_grade = self.state.ending_grade(locked) if locked else "normal"
            if not scene.next_hook:
                scene.next_hook = f"{locked or '该线路'}结局：{ending_grade}"
            if locked and not scene.scene_goal:
                scene.scene_goal = f"{locked}线路的{ending_grade}结局收束"
        return scene

    def _normalize_stage_blocking(self, scene: SceneData) -> None:
        speakers: list[str] = []
        for line in scene.script:
            speaker = line.speaker.strip()
            if not speaker or speaker in ("旁白", "系统", "我", "主角"):
                continue
            if speaker not in speakers:
                speakers.append(speaker)
        if not speakers:
            return

        # Prefer showing the current focus heroine, then the remaining speakers.
        ordered: list[str] = []
        focus_name = self.state.active_heroine or (self.character.name if self.character else "")
        if focus_name and focus_name in speakers:
            ordered.append(focus_name)
        ordered.extend(name for name in speakers if name not in ordered)
        ordered = ordered[:3]

        if len(ordered) == 1:
            positions = [Position.CENTER]
        elif len(ordered) == 2:
            positions = [Position.LEFT, Position.RIGHT]
        else:
            positions = [Position.LEFT, Position.CENTER, Position.RIGHT]

        existing_chars = {
            cmd.character: cmd
            for cmd in scene.stage_commands
            if cmd.action in (StageAction.ENTER, StageAction.MOVE)
        }
        staged_chars = {
            cmd.character
            for cmd in scene.stage_commands
            if cmd.character
        }
        normalized_cmds: list[StageCommand] = []
        touched: set[str] = set()

        for idx, speaker in enumerate(ordered):
            pos = positions[min(idx, len(positions) - 1)]
            existing = existing_chars.get(speaker)
            if existing is not None:
                normalized_cmds.append(
                    StageCommand(
                        action=StageAction.MOVE if existing.action == StageAction.MOVE else StageAction.ENTER,
                        character=speaker,
                        pos=pos,
                        expression=existing.expression,
                    )
                )
            else:
                normalized_cmds.append(
                    StageCommand(
                        action=StageAction.ENTER,
                        character=speaker,
                        pos=pos,
                        expression="default",
                    )
                )
            touched.add(speaker)

        for cmd in scene.stage_commands:
            if cmd.character in touched and cmd.action in (StageAction.ENTER, StageAction.MOVE):
                continue

            # Keep explicit leave commands, but drop stale enter/move commands for non-participating heroines.
            if cmd.action == StageAction.LEAVE:
                normalized_cmds.append(cmd)

        for heroine_name in self._heroine_names():
            if heroine_name in touched:
                continue
            if heroine_name in staged_chars or heroine_name in speakers:
                normalized_cmds.append(
                    StageCommand(
                        action=StageAction.LEAVE,
                        character=heroine_name,
                        pos=Position.CENTER,
                        expression="default",
                    )
                )

        scene.stage_commands = normalized_cmds

    def _bg_key(self, desc: str) -> str:
        """Normalize a background description into a cache key."""
        return desc.lower().strip()[:80]

    def _scene_character_references(self) -> list[Path]:
        refs: list[Path] = []
        if self.character_sprite_path and self.character_sprite_path.exists():
            refs.append(self.character_sprite_path)
        return refs

    def _scene_background_references(self) -> list[Path]:
        refs: list[Path] = []
        if self.current_scene and self.current_scene.background:
            bg_path = Path(self.current_scene.background)
            if bg_path.exists():
                refs.append(bg_path)
        return refs

    def _get_or_generate_bg(
        self,
        desc: str,
        *,
        is_cg: bool = False,
        references: list[Path] | None = None,
    ) -> str | None:
        """Return cached bg path or generate a new one. Thread-safe."""
        key = self._bg_key(desc)
        with self._bg_lock:
            if key in self._bg_cache:
                log.debug("BG cache hit for: %s", key[:40])
                return self._bg_cache[key]
        # Generate outside the lock so we don't block other threads
        try:
            if is_cg:
                path = self.imagen.generate_cg(desc, references=references)
            else:
                path = self.imagen.generate_background(
                    desc,
                    references=references,
                )
            if path:
                with self._bg_lock:
                    self._bg_cache[key] = str(path)
                return str(path)
        except Exception:
            log.exception("Background generation failed for: %s", desc[:60])
        return None

    def _generate_transition_bgs_async(self, scene: SceneData) -> None:
        """Fire-and-forget: pre-generate backgrounds for all scene_transitions."""
        descs = set()
        refs = self._scene_background_references()
        for line in scene.script:
            if line.scene_transition:
                descs.add(line.scene_transition)
        for desc in descs:
            key = self._bg_key(desc)
            with self._bg_lock:
                if key in self._bg_cache:
                    continue
            t = threading.Thread(
                target=self._get_or_generate_bg,
                args=(desc,),
                kwargs={"references": refs},
                daemon=True,
            )
            t.start()

    def get_cached_bg(self, desc: str) -> str | None:
        """Return a cached background path if available (non-blocking)."""
        key = self._bg_key(desc)
        with self._bg_lock:
            return self._bg_cache.get(key)

    @staticmethod
    def _emit_progress(
        progress_cb: ProgressCallback | None,
        step: int,
        total: int,
        message: str,
    ) -> None:
        if not progress_cb:
            return
        try:
            progress_cb(step, total, message)
        except Exception:
            log.debug("Progress callback failed", exc_info=True)

    def init_game(
        self,
        seed_string: str,
        *,
        progress_cb: ProgressCallback | None = None,
    ) -> SceneData:
        """Initialize a new game run from a seed string."""
        self._emit_progress(progress_cb, 1, 5, "解析种子")
        self.seed_hash = hash_seed(seed_string)
        self.atmosphere = derive_initial_atmosphere(self.seed_hash)

        # Generate heroine roster
        self._emit_progress(progress_cb, 2, 5, "生成女主阵容")
        self.heroines.clear()
        self.heroine_sprite_paths.clear()
        variants = self._heroine_variants(seed_string)
        total_variants = len(variants)
        if total_variants:
            self._emit_progress(progress_cb, 2, 5, f"并行生成人设 0/{total_variants}")
        heroine_results: list[CharacterProfile | None] = [None] * total_variants
        completed_heroines = 0
        with ThreadPoolExecutor(max_workers=min(3, max(1, total_variants))) as executor:
            futures = {
                executor.submit(self._generate_single_heroine, idx, seed_hash, trait_code): idx
                for idx, (seed_hash, trait_code) in enumerate(variants)
            }
            for future in as_completed(futures):
                idx = futures[future]
                heroine_results[idx] = future.result()
                completed_heroines += 1
                self._emit_progress(
                    progress_cb,
                    2,
                    5,
                    f"并行生成人设 {completed_heroines}/{total_variants}",
                )
        for heroine in heroine_results:
            if heroine is None:
                continue
            self.heroines.append(heroine)
            self.state.register_heroine(
                heroine.name,
                initial_affection=self.config.initial_affection,
            )
        self._pick_focus_heroine()

        # Generate sprites
        self._emit_progress(progress_cb, 3, 5, "生成角色立绘")
        total_heroines = max(1, len(self.heroines))
        completed_sprites = 0
        self._emit_progress(progress_cb, 3, 5, f"并行生成立绘 0/{total_heroines}")
        with ThreadPoolExecutor(max_workers=min(3, total_heroines)) as executor:
            futures = {
                executor.submit(self._generate_single_sprite, heroine): heroine.name
                for heroine in self.heroines
            }
            for future in as_completed(futures):
                heroine_name, sprite_path = future.result()
                if sprite_path:
                    self.heroine_sprite_paths[heroine_name] = sprite_path
                completed_sprites += 1
                self._emit_progress(
                    progress_cb,
                    3,
                    5,
                    f"并行生成立绘 {completed_sprites}/{total_heroines}",
                )
        self._pick_focus_heroine()

        # Generate first scene
        self._emit_progress(progress_cb, 4, 5, "生成首个场景")
        scene = self.get_next_scene(progress_cb=progress_cb)
        self._emit_progress(progress_cb, 5, 5, "初始化完成")
        return scene

    def get_next_scene(
        self,
        player_choice: str = "",
        choice_delta: dict[str, int] | None = None,
        *,
        progress_cb: ProgressCallback | None = None,
    ) -> SceneData:
        """Generate the next scene, applying any choice effects."""
        self._emit_progress(progress_cb, 1, 6, "应用状态")
        if choice_delta:
            self.state.apply_delta(choice_delta)

        self.state.advance_round()
        self.state.update_route_state()
        focus_heroine = self._pick_focus_heroine()
        random_event = roll_random_event(self.state.round_number, self.state.affection)

        self._emit_progress(progress_cb, 2, 6, "生成剧情")
        try:
            assert focus_heroine is not None
            scene = self.scene_chain.invoke(
                character_profile=focus_heroine,
                cast_summary=self._cast_summary(),
                active_heroine=self.state.active_heroine,
                affection=self.state.affection,
                round_number=self.state.round_number,
                history_summary=self.state.get_history_summary(),
                story_memory=self.state.get_story_memory(),
                route_blueprint=self.state.route_blueprint(),
                ending_target=self._ending_target(),
                last_choice=player_choice,
                random_event=random_event,
                chapter_beat=self.state.chapter_beat,
                route_phase=self.state.route_phase,
                route_locked_to=self.state.route_locked_to,
                progress_cb=lambda message: self._emit_progress(
                    progress_cb,
                    2,
                    6,
                    message,
                ),
            )
            scene = self._postprocess_scene(scene)
        except Exception:
            log.exception("Scene generation failed, using fallback")
            scene = FALLBACK_SCENE

        if scene.game_state_update.is_ending:
            self.state.is_ending = True

        # Record history (multiple lines for longer scenes)
        self._emit_progress(progress_cb, 3, 6, "整理状态")
        self.state.remember_scene(scene)
        if scene.script:
            speakers = set(
                l.speaker for l in scene.script if l.speaker not in ("旁白", "系统")
            )
            opening = scene.script[0].text[:28]
            goal = scene.scene_goal[:24] if scene.scene_goal else "关系推进"
            summary = (
                f"[场景{self.state.round_number}] {', '.join(speakers)}"
                f" | {goal} | {opening}"
            )
            self.state.add_history(summary)
            if self.state.round_number % 3 == 0:
                self.state.memory_fragments.append(
                    generate_memory_fragment(
                        self.state.history,
                        self.state.round_number,
                    )
                )
                self.state.memory_fragments = self.state.memory_fragments[-8:]

        # Generate main background (or CG)
        self._emit_progress(progress_cb, 4, 6, "生成主视觉")
        character_refs = self._scene_character_references()
        background_refs = self._scene_background_references()
        if scene.visual_type == VisualType.CINEMATIC_CG and scene.climax_cg_prompt:
            path = self._get_or_generate_bg(
                scene.climax_cg_prompt,
                is_cg=True,
                references=character_refs + background_refs,
            )
            if path:
                scene.background = path
        elif scene.background:
            path = self._get_or_generate_bg(
                scene.background,
                references=background_refs,
            )
            if path:
                scene.background = path

        # Pre-generate transition backgrounds in background threads (non-blocking)
        self._emit_progress(progress_cb, 5, 6, "预取转场背景")
        self._generate_transition_bgs_async(scene)

        self.current_scene = scene
        self._emit_progress(progress_cb, 6, 6, "场景完成")
        return scene

    def _ending_scene(self) -> SceneData:
        return SceneData(
            scene_id="ending",
            background="beautiful sunset over school rooftop, warm golden light, cherry blossoms",
            script=[
                {
                    "speaker": "旁白",
                    "text": "这段故事，终于画上了句号。",
                    "inner_monologue": "夕阳的余晖洒落，心中满是温暖的回忆。",
                }
            ],
            choices=[
                {"text": "回到主菜单", "target_state_delta": {}},
            ],
            game_state_update={"is_climax": False, "is_ending": True},
        )
