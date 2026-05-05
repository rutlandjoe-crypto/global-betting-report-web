import os
import asyncio
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# =========================================================
# PATH + ENV SETUP
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

# =========================================================
# DEBUG TOKEN CHECK
# =========================================================
print("=" * 60)
print(f"📁 Base directory: {BASE_DIR}")
print(f"📄 .env path: {ENV_PATH}")
print(f"📄 .env exists: {ENV_PATH.exists()}")
print(f"🔑 TOKEN FOUND: {bool(DISCORD_TOKEN)}")
print(f"🔑 TOKEN LENGTH: {len(DISCORD_TOKEN)}")
print(f"🔑 TOKEN START: {DISCORD_TOKEN[:8] if DISCORD_TOKEN else 'EMPTY'}")
print(f"🔑 TOKEN END: {DISCORD_TOKEN[-6:] if DISCORD_TOKEN else 'EMPTY'}")
print("=" * 60)

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is missing or empty in your .env file.")

# =========================================================
# DISCORD INTENTS
# =========================================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================================================
# REPORT FILES
# =========================================================
REPORT_FILES = {
    "mlb": BASE_DIR / "mlb_report.txt",
    "nba": BASE_DIR / "nba_report.txt",
    "nhl": BASE_DIR / "nhl_report.txt",
    "nfl": BASE_DIR / "nfl_report.txt",
    "soccer": BASE_DIR / "soccer_report.txt",
    "fantasy": BASE_DIR / "fantasy_report.txt",
    "betting": BASE_DIR / "betting_odds_report.txt",
    "global": BASE_DIR / "global_sports_report.txt",
}

# =========================================================
# OPTIONAL REPORT GENERATORS
# These will be used if they exist.
# If not, the bot will still work by reading the text files.
# =========================================================
try:
    from get_mlb_report import generate_mlb_report
except Exception as e:
    generate_mlb_report = None
    print(f"⚠️ Could not import generate_mlb_report: {e}")

try:
    from get_nba_report import generate_nba_report
except Exception as e:
    generate_nba_report = None
    print(f"⚠️ Could not import generate_nba_report: {e}")

try:
    from get_nhl_report import generate_nhl_report
except Exception as e:
    generate_nhl_report = None
    print(f"⚠️ Could not import generate_nhl_report: {e}")

try:
    from get_nfl_report import generate_nfl_report
except Exception as e:
    generate_nfl_report = None
    print(f"⚠️ Could not import generate_nfl_report: {e}")

try:
    from get_soccer_report import generate_soccer_report
except Exception as e:
    generate_soccer_report = None
    print(f"⚠️ Could not import generate_soccer_report: {e}")

try:
    from get_fantasy_report import generate_fantasy_report
except Exception as e:
    generate_fantasy_report = None
    print(f"⚠️ Could not import generate_fantasy_report: {e}")

try:
    from get_betting_odds_report import generate_betting_odds_report
except Exception as e:
    generate_betting_odds_report = None
    print(f"⚠️ Could not import generate_betting_odds_report: {e}")

try:
    from get_global_sports_report import generate_global_sports_report
except Exception as e:
    generate_global_sports_report = None
    print(f"⚠️ Could not import generate_global_sports_report: {e}")

GENERATORS = {
    "mlb": generate_mlb_report,
    "nba": generate_nba_report,
    "nhl": generate_nhl_report,
    "nfl": generate_nfl_report,
    "soccer": generate_soccer_report,
    "fantasy": generate_fantasy_report,
    "betting": generate_betting_odds_report,
    "global": generate_global_sports_report,
}

# =========================================================
# HELPERS
# =========================================================
def ensure_report_file(path: Path, label: str) -> None:
    if not path.exists():
        path.write_text(
            f"{label.upper()} REPORT\n\nNo report data is available yet.\n",
            encoding="utf-8"
        )

def read_report_file(path: Path, label: str) -> str:
    ensure_report_file(path, label)
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return f"{label.upper()} REPORT\n\nNo report data is available yet."
        return content
    except Exception as e:
        return f"{label.upper()} REPORT\n\nCould not read report file.\n\nError: {e}"

def split_message(text: str, limit: int = 1900) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks = []
    current = ""

    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]
        current += line

    if current:
        chunks.append(current)

    return chunks

async def maybe_generate_report(label: str) -> str:
    """
    Try the generator first if it exists.
    If it fails, fall back to the txt file.
    """
    generator = GENERATORS.get(label)
    report_path = REPORT_FILES[label]

    if generator is not None:
        try:
            result = generator()

            if asyncio.iscoroutine(result):
                result = await result

            if isinstance(result, str) and result.strip():
                report_path.write_text(result, encoding="utf-8")
                return result.strip()

        except Exception as e:
            print(f"⚠️ Generator failed for {label}: {e}")

    return read_report_file(report_path, label)

async def send_report(interaction: discord.Interaction, label: str) -> None:
    await interaction.response.defer(thinking=True)

    try:
        report_text = await maybe_generate_report(label)
        chunks = split_message(report_text)

        await interaction.followup.send(f"📰 **{label.upper()} report ready**")

        for chunk in chunks:
            await interaction.followup.send(chunk)

    except Exception as e:
        await interaction.followup.send(
            f"❌ Could not deliver the {label.upper()} report.\nError: {e}"
        )

# =========================================================
# EVENTS
# =========================================================
@bot.event
async def on_ready():
    print("=" * 60)
    print(f"✅ Logged in as {bot.user}")
    print(f"🧾 Commands currently loaded in tree: {[cmd.name for cmd in bot.tree.get_commands()]}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} global slash command(s): {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"❌ Slash command sync failed: {e}")
    print("=" * 60)

# =========================================================
# PREFIX COMMANDS
# =========================================================
@bot.command()
async def ping(ctx: commands.Context):
    await ctx.send("🏓 Pong! Bot is online.")

@bot.command()
async def files(ctx: commands.Context):
    lines = []
    for label, path in REPORT_FILES.items():
        exists = "✅" if path.exists() else "❌"
        lines.append(f"{exists} {label}: {path.name}")
    await ctx.send("**Report files:**\n" + "\n".join(lines))

@bot.command()
async def helpme(ctx: commands.Context):
    await ctx.send(
        "**Available commands:**\n"
        "`!ping`\n"
        "`!files`\n"
        "`!mlb`\n"
        "`!nba`\n"
        "`!nhl`\n"
        "`!nfl`\n"
        "`!soccer`\n"
        "`!fantasy`\n"
        "`!betting`\n"
        "`!global`"
    )

@bot.command()
async def mlb(ctx: commands.Context):
    report = await maybe_generate_report("mlb")
    for chunk in split_message(report):
        await ctx.send(chunk)

@bot.command()
async def nba(ctx: commands.Context):
    report = await maybe_generate_report("nba")
    for chunk in split_message(report):
        await ctx.send(chunk)

@bot.command()
async def nhl(ctx: commands.Context):
    report = await maybe_generate_report("nhl")
    for chunk in split_message(report):
        await ctx.send(chunk)

@bot.command()
async def nfl(ctx: commands.Context):
    report = await maybe_generate_report("nfl")
    for chunk in split_message(report):
        await ctx.send(chunk)

@bot.command()
async def soccer(ctx: commands.Context):
    report = await maybe_generate_report("soccer")
    for chunk in split_message(report):
        await ctx.send(chunk)

@bot.command()
async def fantasy(ctx: commands.Context):
    report = await maybe_generate_report("fantasy")
    for chunk in split_message(report):
        await ctx.send(chunk)

@bot.command()
async def betting(ctx: commands.Context):
    report = await maybe_generate_report("betting")
    for chunk in split_message(report):
        await ctx.send(chunk)

@bot.command()
async def global_cmd(ctx: commands.Context):
    report = await maybe_generate_report("global")
    for chunk in split_message(report):
        await ctx.send(chunk)

# =========================================================
# SLASH COMMANDS
# =========================================================
@bot.tree.command(name="ping", description="Check if the bot is online.")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! Bot is online.")

@bot.tree.command(name="mlb", description="Show the latest MLB report.")
async def slash_mlb(interaction: discord.Interaction):
    await send_report(interaction, "mlb")

@bot.tree.command(name="nba", description="Show the latest NBA report.")
async def slash_nba(interaction: discord.Interaction):
    await send_report(interaction, "nba")

@bot.tree.command(name="nhl", description="Show the latest NHL report.")
async def slash_nhl(interaction: discord.Interaction):
    await send_report(interaction, "nhl")

@bot.tree.command(name="nfl", description="Show the latest NFL report.")
async def slash_nfl(interaction: discord.Interaction):
    await send_report(interaction, "nfl")

@bot.tree.command(name="soccer", description="Show the latest soccer report.")
async def slash_soccer(interaction: discord.Interaction):
    await send_report(interaction, "soccer")

@bot.tree.command(name="fantasy", description="Show the latest fantasy report.")
async def slash_fantasy(interaction: discord.Interaction):
    await send_report(interaction, "fantasy")

@bot.tree.command(name="betting", description="Show the latest betting report.")
async def slash_betting(interaction: discord.Interaction):
    await send_report(interaction, "betting")

@bot.tree.command(name="global", description="Show the latest Global Sports Report.")
async def slash_global(interaction: discord.Interaction):
    await send_report(interaction, "global")

@bot.tree.command(name="files", description="Show report file status.")
async def slash_files(interaction: discord.Interaction):
    lines = []
    for label, path in REPORT_FILES.items():
        exists = "✅" if path.exists() else "❌"
        lines.append(f"{exists} {label}: {path.name}")
    await interaction.response.send_message("**Report files:**\n" + "\n".join(lines))

# =========================================================
# RUN BOT
# =========================================================
try:
    bot.run(DISCORD_TOKEN)
except discord.LoginFailure:
    print("❌ Discord login failed: the token is invalid.")
except Exception as e:
    print(f"❌ Bot failed to run due to: {e}")