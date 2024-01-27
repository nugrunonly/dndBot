import openai
import asyncio 
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.environ['API_KEY']

async def make_picture(text):
  summary = openai.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": f"Please turn the following text into a prompt for an image -- {text}. Keep it less than 20 words and only describe one thing from the text to make a good illustration."}], max_tokens = 60)
  print(summary.choices[0].message.content)
  response = openai.images.generate(
  model = "dall-e-3",
  prompt=f'a dnd illustration of {summary.choices[0].message.content}',
  size="1024x1024",
  quality = "standard",
  n=1,
  )
  image_url = response.data[0].url

  with open('image_url.txt', 'w') as file:
      file.write(image_url)
