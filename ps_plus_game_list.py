import re
import json
import aiohttp
import asyncio
import requests
from config import *
from termcolor import cprint
from fake_useragent import UserAgent
from bs4 import BeautifulSoup as Soup


class PS_Plus:
    def __init__(self):
        self.cookies = cookies
        self.headers = headers
        self.games_list = []
        self.formatted_games = []
        self.games_dict = {}
        self.remove = ["+", "’", "'", ".", ":", ",", ";"]
        self.replace = ["/", " "]

    # Gets games grom playstation site
    def get_games(self) -> None:

        try:
            # Get page with all games
            response = requests.get(
                'https://www.playstation.com/en-hk/ps-plus/games/', cookies=cookies, headers=headers)

            # with open("index.html", "w", encoding="utf-8") as f:
            #     f.write(response.text)

            # with open("index.html", "r", encoding="utf-8") as f:
            #     html = f.read()

            html = response.text

            soup = Soup(html, "lxml")

            # Block with all games
            block = soup.find("div", class_="tabs-content")

            # List with all games
            games_blocks = block.find_all("div", class_="tabs__tab-content")

            # Goes through all the games blocks
            for content in games_blocks:
                mini_block = content.find_all("div", class_="box")

                # Finds all blocks with games names
                for triplet in mini_block:
                    try:
                        parbase = triplet.find("div", class_="parbase")
                        games = parbase.find(
                            "div").find_all("p", class_="txt-style-base")

                    # If there are some empty blocks
                    except:
                        continue

                    # Goes through all the games
                    for game in games:
                        if game.text.strip() != "":
                            self.games_list.append(game.text.strip())

        except Exception as ex:
            cprint(f"[SONY_ERROR] {repr(ex)}", "red")

    # Changes the name of the game to match the metacritic link format
    def format_game_name(self) -> None:
        # Goes through all the games
        for game in self.games_list:
            game_name = game.lower().strip()

            # Removes all symbols from self.remove from gamename
            for remove in self.remove:
                if remove in game_name:
                    game_name = game_name.replace(remove, "")

            # Replace all symbols from self.replace from gamename with "-"
            for replace in self.replace:
                if replace in game_name:
                    game_name = game_name.replace(replace, "-")

            if game_name.strip() != "":
                self.formatted_games.append(game_name)

    # Removes parens and their content
    def remove_parens(self, text: str) -> str:
        n = 1
        while n:
            text, n = re.subn(r'\([^()]*\)', '', text)
        return text

    # Gets metacritic score for each game
    async def get_games_meta_score(self, session: aiohttp.ClientSession, url: str, index: int) -> None:
        try:
            headers = {
                "user-agent": UserAgent().random
            }

            r = await session.get(url, headers=headers)

            soup = Soup(await r.text(), "lxml")

            # Sleep every 20 requests
            if index % 20 == 0:
                await asyncio.sleep(1)

            title = soup.find("title").text

            # Pass if page not found
            if "404" in title:
                return

            block = soup.find("div", class_="section product_scores")

            # Trying get metascore
            try:
                metascore = block.find("div", class_="main_details").find(
                    "div", class_="metascore_w").find("span").text
            except:
                metascore = None

            # Trying get userscore
            try:
                userscore = block.find("div", class_="side_details").find(
                    "div", class_="metascore_w").text
            except:
                userscore = None

            # Adds game to gaems dict
            self.games_dict[self.games_list[index]] = {
                "Metascore": metascore,
                "Userscore": userscore
            }

            cprint(
                f"[+] Обработал {self.games_list[index]}", "green")

        except Exception as ex:
            cprint(f"[META_ERROR] {repr(ex)}", "red")

    # Creates tasks for get_games_meta_score function
    async def create_tasks(self) -> None:
        tasks = []
        # Creates async session
        async with aiohttp.ClientSession() as session:
            for i, game in enumerate(self.formatted_games):

                # Checks last 5 symbols of game name
                match game[-5:].lower():
                    case "(ps4)":
                        game = self.remove_parens(game.strip())[:-1]
                        urls = [
                            f"https://www.metacritic.com/game/playstation-4/{game}"]
                    case "(ps5)":
                        game = self.remove_parens(game.strip())[:-1]
                        urls = [
                            f"https://www.metacritic.com/game/playstation-5/{game}"]
                    case _:
                        urls = [
                            f"https://www.metacritic.com/game/playstation-4/{game}",
                            f"https://www.metacritic.com/game/playstation-5/{game}"
                        ]

                # Creates task
                for url in urls:
                    task = asyncio.create_task(
                        self.get_games_meta_score(session, url, i))
                    tasks.append(task)

            # Calls each task from tasks
            await asyncio.gather(*tasks)

    # Creates Json with all games
    def create_json(self) -> None:
        with open(".\\game_list.json", "w", encoding="utf-8") as f:
            json.dump(self.games_dict, f, indent=4, ensure_ascii=False)

    # All in one
    async def get_info(self) -> None:
        self.get_games()
        self.format_game_name()
        await self.create_tasks()
        self.create_json()


async def main():
    ps_plus = PS_Plus()
    await ps_plus.get_info()

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
