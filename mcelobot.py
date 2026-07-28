import discord
from discord.ext import commands
from discord import ui
import json
import random
from flask import Flask, render_template, redirect, send_file
from waitress import serve
import threading
from threading import Thread
import requests
from flask import jsonify
import time


#Server
app = Flask(__name__)


GAMEMODESLIST = {
    "sword": {
        "title": "Sword",
        "info_text": "Classic diamond sword PvP.",
        "kit_url": "https://raw.githubusercontent.com/Soumeh/1.21.1-Assets/refs/heads/1.21.1/assets/minecraft/textures/item/diamond_sword.png",
        "discord_url": "https://discord.gg/bMpMk99aFM"
    },
    "crystal": {
        "title": "Crystal",
        "info_text": "End crystal combat.",
        "kit_url": "https://raw.githubusercontent.com/Soumeh/1.21.1-Assets/refs/heads/1.21.1/assets/minecraft/textures/item/end_crystal.png",
        "discord_url": "https://discord.gg/bMpMk99aFM"
    },
    "mace": {
        "title": "Mace",
        "kit_url": "https://raw.githubusercontent.com/Soumeh/1.21.1-Assets/refs/heads/1.21.1/assets/minecraft/textures/item/mace.png",
        "discord_url": "https://discord.gg/bMpMk99aFM"
    },
    "axe": {
        "title": "Axe",
        "kit_url": "https://raw.githubusercontent.com/Soumeh/1.21.1-Assets/refs/heads/1.21.1/assets/minecraft/textures/item/diamond_axe.png",
        "discord_url": "https://discord.gg/bMpMk99aFM"
    },
    "smp": {
        "title": "SMP",
        "kit_url": "https://raw.githubusercontent.com/Soumeh/1.21.1-Assets/refs/heads/1.21.1/assets/minecraft/textures/block/grass_block_side.png",
        "discord_url": "https://discord.gg/bMpMk99aFM"
    },
    "uhc": {
        "title": "UHC",
        "kit_url": "https://raw.githubusercontent.com/Soumeh/1.21.1-Assets/refs/heads/1.21.1/assets/minecraft/textures/item/golden_apple.png",
        "discord_url": "https://discord.gg/bMpMk99aFM"
    },
    "npot": {
        "title": "NPot",
        "kit_url": "https://raw.githubusercontent.com/Soumeh/1.21.1-Assets/refs/heads/1.21.1/assets/minecraft/textures/item/netherite_helmet.png",
        "discord_url": "https://discord.gg/bMpMk99aFM"
    },
    "potion": {
        "title": "Potion",
        "kit_url": "https://raw.githubusercontent.com/Soumeh/1.21.1-Assets/refs/heads/1.21.1/assets/minecraft/textures/item/splash_potion.png",
        "discord_url": "https://discord.gg/bMpMk99aFM"
    },
    "op": {
        "title": "OP",
        "kit_url": "https://raw.githubusercontent.com/Soumeh/1.21.1-Assets/refs/heads/1.21.1/assets/minecraft/textures/item/diamond_chestplate.png",
        "discord_url": "https://discord.gg/bMpMk99aFM"
    }
}

#Pages
@app.route("/")
def index():
    data=load_elos()
    return render_template("index.html", data=data)

@app.route("/discord")
def disc():
    return redirect("https://discord.gg/bMpMk99aFM")

@app.route("/waveac")
def waveac():
    return send_file("waveac.exe", as_attachment=True, download_name="wave.ac.exe")



#V2
@app.route('/api/v2/profile/<uuid>', methods=['GET'])
def get_profile(uuid):
    db = load_elos()
    target_ign = fetch_ign_from_uuid(uuid)
    
    if not target_ign:
        return jsonify({"error": "Invalid UUID or player does not exist on Mojang."}), 404

    discord_id = None
    raw_data = None
    
    for d_id, p_data in db.items():
        if p_data.get("ign", "").lower() == target_ign.lower():
            discord_id = d_id
            raw_data = p_data
            break
            
    if not raw_data:
        return jsonify({"error": f"Player '{target_ign}' not found in our database."}), 404

    rankings = {}
    total_points = 0
    
    
    for mode in gamemodes:
        elo_key = f"{mode}elo"
        if elo_key in raw_data:
            elo_val = raw_data[elo_key]
            tier_num = elo_to_mctier(elo_val)
            
            if tier_num[:-1] == "LT":
                pos = 1
            else:
                pos = 0

            rankings[mode] = {
                "tier": tier_num[2:],
                "pos": pos,           
                "peak_tier": tier_num[2:],
                "peak_pos": pos,      
                "attained": raw_data[f"{mode}attained"],      
                "retired": False,
                "elo": int(elo_val)
            }

    leaderboard = 0
    overall_rank = 0


    for key, value in raw_data.items():
        if key.endswith("elo"):
            mode = key.replace("elo", "")
            mode_points = int(get_points(value))
            total_points += mode_points

    api_response = {
        "uuid": uuid,
        "name": raw_data.get("ign"),
        "region": raw_data.get("region", "Unknown"), 
        "points": total_points,
        "overall": calculate_overall_rank(db=db, target_discord_id=discord_id),               
        "discord_id": discord_id,       
        "rankings": rankings,
        "badges": [],
        "tests": []
    }

    return jsonify(api_response), 200


@app.route('/api/v2/profile/<uuid>/rankings', methods=['GET'])
def get_profile_rankings(uuid):
    db = load_elos()
    target_ign = fetch_ign_from_uuid(uuid)
    
    if not target_ign:
        return jsonify({"error": "Invalid UUID or player does not exist on Mojang."}), 404

    discord_id = None
    raw_data = None
    
    for d_id, p_data in db.items():
        if p_data.get("ign", "").lower() == target_ign.lower():
            discord_id = d_id
            raw_data = p_data
            break
            
    if not raw_data:
        return jsonify({"error": f"Player '{target_ign}' not found in our database."}), 404

    rankings = {}
    
    
    for mode in gamemodes:
        elo_key = f"{mode}elo"
        if elo_key in raw_data:
            elo_val = raw_data[elo_key]
            tier_num = elo_to_mctier(elo_val)

            if tier_num[:-1] == "LT":
                pos = 1
            else:
                pos = 0

            rankings[mode] = {
                "tier": tier_num[2:],
                "pos": pos,           
                "peak_tier": tier_num[2:],
                "peak_pos": pos,      
                "attained": raw_data[f"{mode}attained"],     
                "retired": False,
                "elo": int(elo_val)
            }

    leaderboard = 0
    overall_rank = 0

    api_response = rankings

    return jsonify(api_response), 200

@app.route('/api/v2/profile/by-name/<name>', methods=['GET'])
def get_profile_by_name(name):
    db = load_elos()
    target_uuid = fetch_uuid_from_ign(name)
    
    if not name:
        return jsonify({"error": "Invalid UUID or player does not exist on Mojang."}), 404

    discord_id = None
    raw_data = None
    
    for d_id, p_data in db.items():
        if p_data.get("ign", "").lower() == name.lower():
            discord_id = d_id
            raw_data = p_data
            break
            
    if not raw_data:
        return jsonify({"error": f"Player '{name}' not found in our database."}), 404

    rankings = {}
    total_points = 0
    
    
    for mode in gamemodes:
        elo_key = f"{mode}elo"
        if elo_key in raw_data:
            elo_val = raw_data[elo_key]
            tier_num = elo_to_mctier(elo_val)
            total_points += int(elo_val)
            if tier_num[:-1] == "LT":
                pos = 1
            else:
                pos = 0
            rankings[mode] = {
                "tier": tier_num[2:],
                "pos": pos,           
                "peak_tier": tier_num[2:],
                "peak_pos": pos,      
                "attained": raw_data[f"{mode}attained"],
                "retired": False,
                "elo": int(elo_val)
            }

    leaderboard = 1
    overall_rank = 1

    overall_points = 0
    for key, value in raw_data.items():
        if key.endswith("elo"):
            mode = key.replace("elo", "")

            mode_points = get_points(value)

            overall_points += mode_points

    

    api_response = {
        "uuid": fetch_uuid_from_ign(name),
        "name": name,
        "region": raw_data.get("region", "Unknown"), 
        "points": overall_points,
        "overall": calculate_overall_rank(db=db, target_discord_id=discord_id),               
        "discord_id": discord_id,       
        "rankings": rankings,
        "badges": [],
        "tests": []
    }

    return jsonify(api_response), 200


@app.route('/api/v2/mode/list', methods=['GET'])
def get_mode_list():
    """ Returns the static list of all supported gamemodes and their icons """
    return jsonify(GAMEMODESLIST), 200

#V1

@app.route('/api/tierlists', methods=['GET'])
def get_mode_list_v1():
    """ Returns the static list of all supported gamemodes and their icons """
    return jsonify(GAMEMODESLIST), 200

@app.route('/api/search_profile/<name>', methods=['GET'])
def get_profile_by_name_v1(name):
    db = load_elos()
    target_uuid = fetch_uuid_from_ign(name)
    
    if not name:
        return jsonify({"error": "Invalid UUID or player does not exist on Mojang."}), 404

    discord_id = None
    raw_data = None
    
    for d_id, p_data in db.items():
        if p_data.get("ign", "").lower() == name.lower():
            discord_id = d_id
            raw_data = p_data
            break
            
    if not raw_data:
        return jsonify({"error": f"Player '{name}' not found in our database."}), 404

    rankings = {}
    total_points = 0
    
    
    for mode in gamemodes:
        elo_key = f"{mode}elo"
        if elo_key in raw_data:
            elo_val = raw_data[elo_key]
            tier_num = elo_to_mctier(elo_val)
            total_points += int(elo_val)
            if tier_num[:-1] == "LT":
                pos = 1
            else:
                pos = 0
            rankings[mode] = {
                "tier": tier_num[2:],
                "pos": pos,           
                "peak_tier": tier_num[2:],
                "peak_pos": pos,      
                "attained": raw_data[f"{mode}attained"],
                "retired": False,
                "elo": int(elo_val)
            }

    leaderboard = 1
    overall_rank = 1

    overall_points = 0
    for key, value in raw_data.items():
        if key.endswith("elo"):
            mode = key.replace("elo", "")

            mode_points = get_points(value)

            overall_points += mode_points

    

    api_response = {
        "uuid": fetch_uuid_from_ign(name),
        "name": name,
        "region": raw_data.get("region", "Unknown"), 
        "points": overall_points,
        "overall": calculate_overall_rank(db=db, target_discord_id=discord_id),                      
        "rankings": rankings,
        "badges": []
    }

    return jsonify(api_response), 200


@app.route('/api/profile/<uuid>', methods=['GET'])
def get_profile_v1(uuid):
    db = load_elos()
    target_ign = fetch_ign_from_uuid(uuid)
    
    if not target_ign:
        return jsonify({"error": "Invalid UUID or player does not exist on Mojang."}), 404

    discord_id = None
    raw_data = None
    
    for d_id, p_data in db.items():
        if p_data.get("ign", "").lower() == target_ign.lower():
            discord_id = d_id
            raw_data = p_data
            break
            
    if not raw_data:
        return jsonify({"error": f"Player '{target_ign}' not found in our database."}), 404

    rankings = {}
    total_points = 0
    
    
    for mode in gamemodes:
        elo_key = f"{mode}elo"
        if elo_key in raw_data:
            elo_val = raw_data[elo_key]
            tier_num = elo_to_mctier(elo_val)
            
            if tier_num[:-1] == "LT":
                pos = 1
            else:
                pos = 0

            rankings[mode] = {
                "tier": tier_num[2:],
                "pos": pos,           
                "peak_tier": tier_num[2:],
                "peak_pos": pos,      
                "attained": raw_data[f"{mode}attained"],      
                "retired": False,
                "elo": int(elo_val)
            }

    leaderboard = 0
    overall_rank = 0


    for key, value in raw_data.items():
        if key.endswith("elo"):
            mode = key.replace("elo", "")
            mode_points = int(get_points(value))
            total_points += mode_points

    api_response = {
        "uuid": uuid,
        "name": raw_data.get("ign"),
        "region": raw_data.get("region", "Unknown"), 
        "points": total_points,
        "overall": calculate_overall_rank(db=db, target_discord_id=discord_id),                    
        "rankings": rankings,
        "badges": [],
    }

    return jsonify(api_response), 200

@app.route('/api/v2/rankings/<uuid>', methods=['GET'])
def get_profile_rankings_v1(uuid):
    db = load_elos()
    target_ign = fetch_ign_from_uuid(uuid)
    
    if not target_ign:
        return jsonify({"error": "Invalid UUID or player does not exist on Mojang."}), 404

    discord_id = None
    raw_data = None
    
    for d_id, p_data in db.items():
        if p_data.get("ign", "").lower() == target_ign.lower():
            discord_id = d_id
            raw_data = p_data
            break
            
    if not raw_data:
        return jsonify({"error": f"Player '{target_ign}' not found in our database."}), 404

    rankings = {}
    
    
    for mode in gamemodes:
        elo_key = f"{mode}elo"
        if elo_key in raw_data:
            elo_val = raw_data[elo_key]
            tier_num = elo_to_mctier(elo_val)

            if tier_num[:-1] == "LT":
                pos = 1
            else:
                pos = 0

            rankings[mode] = {
                "tier": tier_num[2:],
                "pos": pos,           
                "peak_tier": tier_num[2:],
                "peak_pos": pos,      
                "attained": raw_data[f"{mode}attained"],     
                "retired": False,
                "elo": int(elo_val)
            }

    leaderboard = 0
    overall_rank = 0

    api_response = rankings

    return jsonify(api_response), 200

def run_flask():
    serve(app=app,host="0.0.0.0", port=21957)

#DC BOT
bot = commands.Bot(command_prefix='.', intents=discord.Intents.all())


def get_points(elo_str):
    """ 
    Converts an Elo string into a (Tier, Pos, Points) tuple.
    HT (High Tier) -> Pos 0
    LT (Low Tier)  -> Pos 1
    """
    if not elo_str:
        return 2
    
    e = int(elo_str)
    if e >= 1800: return 60  # HT1
    if e >= 1600: return 54  # LT1
    if e >= 1400: return 48  # HT2
    if e >= 1200: return 41  # LT2
    if e >= 1000: return 34  # HT3
    if e >= 800:  return 28  # LT3
    if e >= 600:  return 20  # HT4
    if e >= 400:  return 14  # LT4
    if e >= 200:  return 8   # HT5
    return 2                 # LT5


def calculate_overall_rank(db, target_discord_id):
    """ Tallies everyone's points and finds the requested player's exact rank. """
    if not target_discord_id:
        return None

    leaderboard = []
    
    for d_id, p_data in db.items():
        pts = 0
        for key, value in p_data.items():
            if key.endswith("elo"):
                mode_pts = get_points(value)
                pts += mode_pts
        leaderboard.append({"discord_id": d_id, "points": pts})

    leaderboard.sort(key=lambda x: x["points"], reverse=True)

    for index, p in enumerate(leaderboard):
        if p["discord_id"] == target_discord_id:
            return index + 1
            
    return None


def is_older_than_2_hours(timestamp):
    return (time.time() - timestamp) > 7200

def load_elos():
    with open("results.json", "r") as f:
        return json.load(f)

def save_elos(data):
    with open("results.json", "w") as f:
        json.dump(data, f, indent=4)

def fetch_ign_from_uuid(uuid):
    """ Hits Mojang API to get Name from UUID """
    try:
        clean_uuid = uuid.replace("-", "")
        response = requests.get(f"https://api.mojang.com/user/profile/{clean_uuid}", timeout=5)
        if response.status_code == 200:
            return response.json().get("name")
    except Exception as e:
        print(f"Error fetching from Mojang: {e}")
    return None

def fetch_uuid_from_ign(ign):
    """ Hits Mojang API to get UUID from Name """
    try:
        response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{ign}", timeout=5)
        if response.status_code == 200:
            raw_id = response.json().get("id")
            return f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"
    except Exception as e:
        print(f"Error fetching from Mojang: {e}")
    return None


def elo_to_mctier(elo_value) -> str:
    """
    Convert an Elo value (string or int) into the corresponding McTiers rank.
    Returns 'Invalid Elo' if the input cannot be parsed.
    """


    try:
        elo = int(elo_value)
    except (ValueError, TypeError):
        return "Invalid Elo"

    tiers = [
        (0, 200, "LT5"),
        (200, 400, "HT5"),
        (400, 600, "LT4"),
        (600, 800, "HT4"),
        (800, 1000, "LT3"),
        (1000, 1200, "HT3"),
        (1200, 1400, "LT2"),
        (1400, 1600, "HT2"),
        (1600, 1800, "LT1"),
        (1800, 2001, "HT1"),
    ]

    for low, high, rank in tiers:
        if low <= elo < high:
            return rank

    return "Unranked"

class DeleteChannel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Close Ticket (Instant Delete)", style=discord.ButtonStyle.danger)
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()


gamemodes = {
    "crystal", "sword", "axe", "mace", "smp", "uhc", "potion", "npot", "op"
}

class MyModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(timeout=None, *args, **kwargs)
        
        self.add_item(discord.ui.TextInput(label="Username", style=discord.TextStyle.short, placeholder="ex. executedd"))
        self.add_item(discord.ui.TextInput(label="Prefered Server", style=discord.TextStyle.short, placeholder="ex. mcpvp.club"))
        self.add_item(discord.ui.TextInput(label="Region", style=discord.TextStyle.short, placeholder="ex. EU"))
        self.add_item(discord.ui.TextInput(label="Gamemode",style=discord.TextStyle.short, placeholder="ex. Crystal"))

    async def on_submit(self, interaction: discord.Interaction):
        gamemode = str(self.children[3])
        if gamemode.lower() not in gamemodes:
            await interaction.response.send_message(
                f"Gamemode {gamemode.capitalize()} does not exist, please check the spelling",
                ephemeral=True
            )
            return ""
        if str(self.children[1]).find(".") == -1:
            await interaction.response.send_message(
                f"Server {str(self.children[1])} does not exist, please check the spelling",
                ephemeral=True
            )
            return ""
        
        if gamemode.lower() == "uhc":
            role_name = "UHC Tester"
        elif gamemode.lower() == "smp":
        	role_name = "SMP Tester"
        elif gamemode.lower() == "op":
            role_name = "OP Tester"
        elif gamemode.lower() == "npot":
            role_name = "NPot Tester"
        else:
            role_name = f"{gamemode.capitalize()} Tester"

        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=role_name)
        
        user = guild.get_member(interaction.user.id)
       
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.get_role(role.id): discord.PermissionOverwrite(read_messages=True),
            user: discord.PermissionOverwrite(read_messages=True)
        }
        catagory = discord.utils.get(guild.categories, id=1477309964358910112)
        if discord.utils.get(catagory.channels, name=user.name) == None:
            data = load_elos()

            user_id = str(interaction.user.id)

            if user_id not in data:
                data[user_id] = {}

            try:
                if data[user_id][f"{gamemode.lower()}attained"]:
                    if is_older_than_2_hours(data[user_id][f"{gamemode.lower()}attained"]) == False:
                        await interaction.response.send_message("You are on cooldown for a test in this gamemode", ephemeral=True)
                        return ""
            except:
                print("Not tested in gamemode!")
                    

            channel = await discord.Guild.create_text_channel(self=interaction.guild, name=interaction.user.name, category=catagory, overwrites=overwrites)
            
            await interaction.response.send_message(
                f"Ticket created <#{channel.id}>",
                ephemeral=True,
            )

            embed = discord.Embed(
                title="Elo Test",
                description=f"IGN >> ```{self.children[0]}``` \nPrefered Server IP >> ```{self.children[1]}``` \n Region >> ```{self.children[2]}``` \n Gamemode >> ```{self.children[3]}```",
                color=discord.Colour.from_rgb(255, 161, 127)
            )
            
            



            data[user_id]["ign"] = self.children[0].value
            data[user_id]["region"] = str(self.children[2].value).upper()
            save_elos(data=data)

            await channel.send(role.mention, embed=embed, view=DeleteChannel())
        else: 
            await interaction.response.send_message("You already have a ticket open!", ephemeral=True)
            return ""



class MyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create a Ticket", style=discord.ButtonStyle.success, custom_id="MakeTicket")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = MyModal(title="Test Form")
        await interaction.response.send_modal(modal)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.loop.create_task(send_startup_message())



async def send_startup_message():
    await bot.wait_until_ready()
    channel = bot.get_channel(1477402849301500110)
    if channel:
        embed = discord.Embed(
            title="ELO Test",
            description=f"Available Gamemodes: ```{', '.join(gamemodes)}``` \nTo get elo tested for our leaderboard, please press the button below and enter your ign and prefered server",
            color=discord.Colour.from_rgb(255, 161, 127)
        )
        await channel.purge(limit=None)
        await channel.send(embed=embed,view=MyView())
    else:
        print("Channel not found!")

@bot.command()
async def result(ctx, elo: str, user: discord.User, score:str, gamemode:str):
    embed = discord.Embed(
    title=f"Test Result",
    description=f"Player Tested >> {user.mention} \n\nGamemode >> {gamemode.capitalize()} \nElo >> {elo} \nMCTiers rank conversion >> {elo_to_mctier(elo_value=elo)} \nTester >> {ctx.author.mention} \nScore >> {score}",
    color=discord.Colour.from_rgb(255, 161, 127)
)   
    role = discord.utils.get(ctx.guild.roles, name="Tester")
    if role in ctx.author.roles and gamemode.lower() in gamemodes:
        await bot.get_channel(1477297561688866956).send(embed=embed)
        data = load_elos()
        user_id = str(user.id)



        guild = ctx.guild
        member = ctx.guild.get_member(user.id)

        if gamemode.lower() == "uhc":
            roletogive = "UHC"
        elif gamemode.lower() == "smp":
        	roletogive = "SMP"
        elif gamemode.lower() == "op":
            roletogive = "OP"
        elif gamemode.lower() == "npot":
            roletogive = "NPot"
        else:
            roletogive = gamemode.capitalize()
        
        role = discord.utils.get(guild.roles, name=f"{elo_to_mctier(elo)} {roletogive}")
        if not role:
            await guild.create_role(name=f"{elo_to_mctier(elo)} {roletogive}")

        role = discord.utils.get(guild.roles, name=f"{elo_to_mctier(elo)} {roletogive}")
        await member.add_roles(role)
        role = discord.utils.get(guild.roles, name="Tested")
        await member.add_roles(role)

        try:
            if data[user_id][f"{gamemode.lower()}elo"] != None:
                role = discord.utils.get(guild.roles, name=f"{elo_to_mctier(data[user_id][f'{gamemode.lower()}elo'])} {roletogive}")
                await member.remove_roles(role)
        except:
            print("No elo defined!")

        data[user_id][f"{gamemode.lower()}elo"] = elo
        data[user_id][f"{gamemode.lower()}attained"] = int(time.time())
        save_elos(data=data)
        await ctx.send("Sent result!")
    else:
        await ctx.send("You do not have Tester Permissions to give a result or you have entered a incorrect gamemode!")


@bot.command()
async def elo(ctx, user:discord.User, gamemode:str):
    data = load_elos()
    user_id = str(user.id)

    if user_id not in data:
        await ctx.send(f"**{user.display_name}** has no elo recorded")
        return
    try:
        elo_value = data[user_id][f"{gamemode.lower()}elo"]
        await ctx.send(f"**{user.display_name}** has **{elo_value}** Elo in **{gamemode.capitalize()}** ")
    except:
        await ctx.send(f"**{user.display_name}** isnt tested **{gamemode.capitalize()}**")

@bot.command()
async def clear(ctx):
    role = discord.utils.get(ctx.guild.roles, name="Mod")
    role1 = discord.utils.get(ctx.guild.roles, name="Admin")
    role2 = discord.utils.get(ctx.guild.roles, name="Owner")

    if role in ctx.author.roles or role1 in ctx.author.roles or role2 in ctx.author.roles:
        await ctx.channel.purge(limit=None)
    else:
        await ctx.send("You do not have permission to execute this command")

@bot.command()
async def lockdown(ctx):
    role = discord.utils.get(ctx.guild.roles, name="Mod")
    role1 = discord.utils.get(ctx.guild.roles, name="Admin")
    role2 = discord.utils.get(ctx.guild.roles, name="Owner")

    if role in ctx.author.roles or role1 in ctx.author.roles or role2 in ctx.author.roles:
        perms = ctx.channel.overwrites_for(ctx.guild.default_role)
        perms.send_messages=False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=perms)
        await ctx.send(f"Successfully locked the current channel")
    else:
        await ctx.send("You do not have permission to execute this command")

@bot.command()
async def unlockdown(ctx):
    role = discord.utils.get(ctx.guild.roles, name="Mod")
    role1 = discord.utils.get(ctx.guild.roles, name="Admin")
    role2 = discord.utils.get(ctx.guild.roles, name="Owner")

    if role in ctx.author.roles or role1 in ctx.author.roles or role2 in ctx.author.roles:
        perms = ctx.channel.overwrites_for(ctx.guild.default_role)
        perms.send_messages=None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=perms)
        await ctx.send(f"Successfully unlocked the current channel")
    else:
        await ctx.send("You do not have permission to execute this command")

@bot.command()
async def slowmode(ctx, time_val:str):
    role = discord.utils.get(ctx.guild.roles, name="Mod")
    role1 = discord.utils.get(ctx.guild.roles, name="Admin")
    role2 = discord.utils.get(ctx.guild.roles, name="Owner")

    if role in ctx.author.roles or role1 in ctx.author.roles or role2 in ctx.author.roles:
        try:
            time = int(time_val)
        except (ValueError, TypeError):
             await ctx.send("Invalid Time!")

        await ctx.channel.edit(slowmode_delay=time)
        await ctx.send(f"Successfully set slowmode to {time} seconds")
    else:
        await ctx.send("You do not have permission to execute this command")

@bot.command()
async def wipe(ctx, user:discord.User):
    role = discord.utils.get(ctx.guild.roles, name="Mod")
    role1 = discord.utils.get(ctx.guild.roles, name="Admin")
    role2 = discord.utils.get(ctx.guild.roles, name="Owner")

    if role in ctx.author.roles or role1 in ctx.author.roles or role2 in ctx.author.roles:
        data = load_elos()
        user_id = str(user.id)

        if user_id in data:
            del data[user_id]

        save_elos(data=data)
        await ctx.send(f"Successfully wiped {user.display_name}")

@bot.command()
async def kick(ctx, user:discord.User, reason:str):
    role = discord.utils.get(ctx.guild.roles, name="Mod")
    role1 = discord.utils.get(ctx.guild.roles, name="Admin")
    role2 = discord.utils.get(ctx.guild.roles, name="Owner")

    if role in ctx.author.roles or role1 in ctx.author.roles or role2 in ctx.author.roles:
        guild = ctx.guild
        member = guild.get_member(user.id)
        await member.kick(reason=reason)
        await ctx.send(f"Successfully kicked {user.display_name}")


@bot.command()
async def getalluseridsandusernames(ctx):
    guild = bot.get_guild(ctx.guild.id)
    for member in guild.members:
        print(f"member:{member.display_name} userid:{member.id}")


@bot.command()
async def closeticket(ctx):
    if ctx.channel.category_id == 1477309964358910112:
        await ctx.channel.delete()

Thread(target=run_flask, daemon=True).start()
      



# region - Token
bot.run("")
# endregion