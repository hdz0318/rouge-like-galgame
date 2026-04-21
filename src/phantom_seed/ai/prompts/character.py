"""Character generation prompt helpers."""

from phantom_seed.ai.prompts.system import CHARACTER_SYSTEM_MESSAGE

CHARACTER_PROMPT_TEMPLATE = """\
请根据以下种子信息，生成一个用于大学校园浪漫视觉小说的角色档案。

【强制约束】该角色必须是 18 岁以上的大学生或成年人，不允许设计中学生或未成年人。

种子哈希值: {seed_hash}
随机特征码: {trait_code}

角色设计要求：
- 年龄：18 岁以上，大学在读或刚毕业的成年人
- 外表成熟迷人，性格鲜明讨喜
- 必须有一个核心魅力点和至少两个让人心动的个人特质
- 说话方式独特，有口头禅或特殊语气
- 外貌描述要有辨识度（用于AI绘图），偏向成熟美丽的大学生风格（不含制服、水手服等学生制服元素）

请严格按照以下 JSON 格式输出：
```json
{{
  "name": "角色名字（日式风格，姓+名）",
  "personality": "表面性格描述（2句话）。内在性格描述（2句话）。核心魅力点（1句话）",
  "speech_pattern": "口癖、说话方式、语气特征的详细描述（3-4句话）",
  "visual_description": "详细英文外貌描述用于AI绘图：an attractive adult university student woman, hair color/style, eye color, casual stylish clothing (NOT a school uniform, NOT sailor uniform), distinguishing features, overall aesthetic（50字以上）",
  "signature_look": "一句话概括她最不可替代的视觉识别点，供后续多张立绘和 CG 保持一致",
  "backstory": "成长经历和情感羁绊，塑造角色深度的背景（3-5句话）",
  "secrets": ["隐藏的一面1", "让人心动的特质2", "不为人知的小习惯3"],
  "relationship_to_player": "与主角的初始关系和可能的恋爱发展方向"
}}
```"""


def build_character_messages(seed_hash: str, trait_code: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": CHARACTER_SYSTEM_MESSAGE},
        {
            "role": "user",
            "content": CHARACTER_PROMPT_TEMPLATE.format(
                seed_hash=seed_hash,
                trait_code=trait_code,
            ),
        },
    ]
