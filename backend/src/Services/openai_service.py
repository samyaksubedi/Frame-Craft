from openai import AsyncOpenAI
import base64
from Configs.env import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def generate_thumbnail(prompt: str, style_prompt: str, headshot_url) -> bytes:
    """Use the Response API with gpt-image-2 as a built-in image_generation tool .
    Pass the headshot URL directly as an imput_image.
    """
    full_prompt = f"""{style_prompt} \n\n User request: {prompt}\n\n
    Important : The generated thumbnail MUST prominently feature the person shown in the provided reference headshot photo. Keep their likeness accurate.
    """

    response = await client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": headshot_url},
                    {"type": "input_text", "text": full_prompt},
                ],
            },
        ],
        tools=[
            {
                "type": "image_generation",
                "model": "gpt-image-1-mini",
                "size": "1536x1024",
                "quality": "high",
                "output_format": "png",
            }
        ],
    )

    # response.output = [
    #     { type: "text",                  result: "Here's your image!" },   # optional text
    #     { type: "image_generation_call", result: "<base64 string>" },      # the image
    #     { type: "text",                  result: "Let me know if..." },    # optional text
    # ]

    image_data = [
        output.result  # grab the base64 string
        for output in response.output  # loop all output blocks
        if output.type == "image_generation_call"  # only image blocks
    ]

    if image_data:
        image_base64 = image_data[0]  # first image (could request multiple)

        return base64.b64decode(image_base64)
    raise RuntimeError("No image generation result found in the response")
