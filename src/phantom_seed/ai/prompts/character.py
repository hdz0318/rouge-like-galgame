"""Character generation prompt helpers."""

from phantom_seed.ai.prompts.system import CHARACTER_SYSTEM_MESSAGE

CHARACTER_PROMPT_TEMPLATE = """\
请根据以下种子信息，生成一个用于大学校园浪漫视觉小说的角色档案。

【强制约束】该角色必须是 18 岁以上的大学生或成年人，不允许设计中学生或未成年人。
【强制约束】角色视觉设计必须服务于“日本动漫风格的商业 galgame / 美少女游戏”立绘与 CG 生成，禁止偏写实、欧美漫画、3D 渲染、真人摄影感或韩漫厚涂风格。

种子哈希值: {seed_hash}
随机特征码: {trait_code}

角色设计要求：
- 年龄：18 岁以上，大学在读或刚毕业的成年人
- 外表成熟迷人，性格鲜明讨喜
- 必须有一个核心魅力点和至少两个让人心动的个人特质
- 说话方式独特，有口头禅或特殊语气
- 外貌描述要有辨识度（用于AI绘图），偏向成熟美丽的大学生风格（不含制服、水手服等学生制服元素）
- `visual_description` 必须直接面向图像模型编写，明确强调 Japanese anime, galgame, bishoujo game heroine, visual novel sprite / CG aesthetic
- `signature_look` 需要足够稳定，方便后续多张日系 galgame 立绘、背景合成和高潮 CG 保持统一人设
- 整体要简洁克制，避免长篇大论；每个字段只写最有辨识度的信息
- 输出必须是完整 JSON，禁止解释、禁止补充说明、禁止 Markdown 代码块

请严格按照以下 JSON 格式输出：
{{
  "name": "角色名字（日式风格，姓+名）",
  "personality": "表面性格1句，内在性格1句，核心魅力点1句",
  "speech_pattern": "口癖和语气特征，共2句以内",
  "visual_description": "英文外貌描述用于AI绘图：必须写成适合日本动漫 galgame 立绘生成的英文 prompt，例如 an attractive adult university student woman in authentic Japanese anime galgame style, hair color/style, eye color, stylish casual outfit (NOT a school uniform, NOT sailor uniform), distinguishing features, bishoujo visual novel heroine aesthetic（30-55英文词）",
  "signature_look": "一句话概括她最不可替代的视觉识别点，供后续多张立绘和 CG 保持一致",
  "backstory": "成长经历和情感羁绊，2-3句",
  "secrets": ["隐藏的一面1", "让人心动的特质2", "不为人知的小习惯3"],
  "relationship_to_player": "与主角的初始关系和可能的发展方向，2句以内"
}}
"""


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
