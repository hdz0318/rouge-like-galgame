"""Visual prompt templates for image generation (plain strings, not LangChain)."""

VISUAL_PROMPT_TEMPLATE = """\
PREMIUM JAPANESE VISUAL NOVEL SPRITE, CONSISTENT POLISHED ANIME RENDERING, ONE SINGLE HEROINE ONLY. \
full body standing character, entire head to feet visible, centered composition, upright posture, \
front-facing or slight 3/4 facing, clean silhouette, calm readable pose, {description}, \
pure white or transparent-style plain background, no props, no furniture, no scenery, no text, \
NO OTHER PEOPLE, NO SECOND CHARACTER, NO CROPPED BODY, NO CUT-OFF FEET, NO EXTRA LIMBS, \
NO CHARACTER SHEET, NO MULTIPLE POSES, NO MULTIPLE EXPRESSIONS, NO SPLIT PANEL, SINGLE IMAGE ONLY, \
uniform visual novel sprite style, refined line art, soft cel shading, stable proportions, elegant colors\
"""

CG_PROMPT_TEMPLATE = """\
premium anime visual novel CG, consistent character design, {description}, \
warm lighting, cinematic composition, \
high detail, emotional scene, visual novel style, pastel tones\
"""

BACKGROUND_PROMPT_TEMPLATE = """\
anime visual novel background illustration, no characters, no people, {description}, \
detailed environment art, warm lighting, soft colors, inviting atmosphere, \
painterly style, high quality background art\
"""
