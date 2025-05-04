from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContext
import asyncio
from dotenv import load_dotenv
from pydantic import SecretStr
import os

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", api_key=SecretStr(os.getenv("GEMINI_API_KEY"))
)

config = BrowserContextConfig(
    save_recording_path="./recs",
)

# Configure the browser to connect to your Chrome instance
browser = Browser(
    config=BrowserConfig(
        # Specify the path to your Chrome executable
        chrome_instance_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS path
        # For Windows, typically: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
        # For Linux, typically: '/usr/bin/google-chrome',
    )
)

context = BrowserContext(browser=browser, config=config)


async def main():
    agent = Agent(
        task="How is the lates activities of Isaac Kargar on GitHub?",
        llm=llm,
        browser=browser,
        browser_context=context,
    )
    await agent.run()

    input("Press Enter to close the browser...")
    await browser.close()


asyncio.run(main())
