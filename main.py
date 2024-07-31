from config import key, token
import asyncio
import time
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Voice, Message, FSInputFile
from openai import OpenAI
from aiogram.client.bot import DefaultBotProperties

# Initialize OpenAI client with API key from config
client = OpenAI(api_key=key)
router = Router()
bot = Bot(token=token, defaultproperties=DefaultBotProperties(parse_mode='HTML'))


@router.message()
async def handle_voice_message(message: Message):
    """
    Handle incoming voice messages by downloading the voice file.

    Args:
        message (Message): The incoming message object.
    """
    # Extract necessary information from the message
    chat_id = str(message.chat.id)
    unique_name = str(int(time.time()))
    save_path = f'{unique_name}.mp3'

    # Get the voice file id and download it
    voice = message.voice
    file_id = voice.file_id
    voice_file = await bot.get_file(file_id)
    await bot.download_file(voice_file.file_path, save_path)

    # Perform speech-to-text conversion
    try:
        speech_text = await stt(f'{save_path}')
    except Exception as e:
        await message.reply(f'Error: {e}')
        return

    # Generate response using GPT
    gpt_answer = await ask_gpt(speech_text)

    # Generate text-to-speech audio file
    unique_name = str(int(time.time()))
    save_path = f'{unique_name}'
    await tts(gpt_answer, save_path)

    # Send the generated voice message
    audio_file = FSInputFile(f'{save_path}')
    await bot.send_voice(chat_id=chat_id, voice=audio_file)


async def stt(unique_name):
    """
    Perform speech-to-text conversion for the given audio file.

    Args:
        unique_name (str): The unique name of the audio file.

    Returns:
        str: The transcribed text.
    """
    audio_file = open(f'{unique_name}', 'rb')
    transcription = client.audio.transcriptions.create(
        model='whisper-1',
        file=audio_file
    )
    print(transcription.text)
    return transcription.text


async def tts(text, unique_name):
    """
    Generate a text-to-speech audio file for the given text.

    Args:
        text (str): The text to convert to speech.
        unique_name (str): The unique name for the generated audio file.
    """
    speech_file_path = f'{unique_name}'
    response = client.audio.speech.create(
        model='tts-1',
        voice='nova',
        input=f'{text}',
    )

    with open(speech_file_path, 'wb') as f:
        f.write(response.content)
    print('Finished writing audio file')


async def ask_gpt(text):
    """
    Generate a response using the GPT model.

    Args:
        text (str): The input text to generate a response.

    Returns:
        str: The generated response.
    """
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': f'{text}'},
        ]
    )
    return response.choices[0].message.content


async def main():
    """
    Main function to start the bot.
    """
    print('Bot started')
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher()
    dp.include_routers(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())