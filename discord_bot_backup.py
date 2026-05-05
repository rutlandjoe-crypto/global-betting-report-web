import os
import sys
import asyncio
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# =========================================================
# PATH / ENV SETUP
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "").strip()

if not DISCORD_TOKEN:
    raise ValueError(
        "DISCORD_TOKEN is not set. Put it in .env as DISCORD_TOKEN=your_token_here"
    )

# =========================================================
# DISCORD SETUP
# =========================================================

intents = discord.Intents.default()
intents.message_content = True  # helps if you ever use prefix commands too

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================================================
# REPORT CONFIG
# =========================================================

REPORTS = {
    "mlb": {
        "script": BASE_DIR / "mlb_agent.py",
        "report": BASE_DIR / "mlb_report.txt",
        "description": "Generate and show the latest MLB report.",
    },
    "nba": {
        "script": BASE_DIR / "get_nba_report.py",
        "report": BASE_DIR / "nba_report.txt",
        "description": "Generate and show the latest NBA report.",
    },
    "nhl": {
        "script": BASE_DIR / "get_nhl_report.py",
        "report": BASE_DIR / "nhl_report.txt",
        "description": "Generate and show the latest NHL report.",
    },
    "nfl": {
        "script": BASE_DIR / "get_nfl_report.py",
        "report": BASE_DIR / "nfl_report.txt",
        "description": "Generate and show the latest NFL report.",
    },
    "soccer": {
        "script": BASE_DIR / "get_soccer_report.py",
        "report": BASE_DIR / "soccer_report.txt",
        "description": "Generate and show the latest soccer report.",
    },
    "global": {
        "script": BASE_DIR / "global_sports_report.py",
        "report": BASE_DIR / "global_sports_report.txt",
        "description": "Generate and show the latest global sports report.",
    },
    "fantasy": {
        "script": BASE_DIR / "fantasy_report.py",
        "report": BASE_DIR / "fantasy_report.txt",
        "description": "Generate and show the latest fantasy report.",
    },
    "ncaafb": {
        "script": BASE_DIR / "ncaafb_report.py",
        "report": BASE_DIR / "ncaafb_report.txt",
        "description": "Generate and show the latest NCAAFB report.",
    },
    "betting": {
        "script": BASE_DIR / "betting_odds_report.py",
        "report": BASE_DIR / "betting_odds_report.txt",
        "description": "Generate and show the latest betting report.",
    },
}

AVAILABLE_REPORTS = {
    name: cfg for name, cfg in REPORTS.items() if cfg["script"].exists()
}

# =========================================================
# HELPERS
# =========================================================

def split_text(text: str, limit: int = 1900) -> list[str]:
    text = (text or "").strip()
    if not text:
        return ["No report content available."]

    chunks = []
    remaining = text

    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


async def run_script(script_path: Path) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(BASE_DIR),
    )

    stdout, stderr = await process.communicate()

    out_text = stdout.decode("utf-8", errors="ignore").strip()
    err_text = stderr.decode("utf-8", errors="ignore").strip()

    return process.returncode, out_text, err_text


def read_report(report_path: Path) -> str:
    if not report_path.exists():
        return ""
    try:
        return report_path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


async def send_long_message(interaction: discord.Interaction, text: str):
    chunks = split_text(text, 1900)
    for chunk in chunks:
        await interaction.followup.send(f"```{chunk}```")


async def generate_and_send_report(interaction: discord.Interaction, report_key: str):
    cfg = AVAILABLE_REPORTS.get(report_key)

    if not cfg:
        await interaction.followup.send(f"`{report_key}` is not configured.")
        return

    script_path = cfg["script"]
    report_path = cfg["report"]

    if not script_path.exists():
        await interaction.followup.send(f"Script not found: `{script_path.name}`")
        return

    return_code, stdout_text, stderr_text = await run_script(script_path)

    if return_code != 0:
        error_text = stderr_text or stdout_text or "Unknown error."
        await interaction.followup.send(f"Report generation failed for `{report_key}`.")
        await send_long_message(interaction, error_text[:6000])
        return

    report_text = read_report(report_path)

    if not report_text:
        report_text = stdout_text

    if not report_text:
        await interaction.followup.send(
            f"`{report_key}` ran, but no report content was produced."
        )
        return

    await send_long_message(interaction, report_text)

# =========================================================
# EVENTS
# =========================================================

@bot.event
async def on_ready():
    try:
        if DISCORD_GUILD_ID:
            guild_obj = discord.Object(id=int(DISCORD_GUILD_ID))
            synced = await bot.tree.sync(guild=guild_obj)
            sync_target = f"guild {DISCORD_GUILD_ID}"
        else:
            synced = await bot.tree.sync()
            sync_target = "global"

        print("=" * 60)
        print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
        print(f"📁 Base directory: {BASE_DIR}")
        print(f"🏁 Commands ready: {', '.join(sorted(AVAILABLE_REPORTS.keys()))}")
        print(f"✅ Slash command tree synced: {len(synced)} command(s) to {sync_target}")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Failed to sync command tree: {e}")

# =========================================================
# BASIC COMMANDS
# =========================================================

@bot.tree.command(name="ping", description="Check if the bot is online.")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")


@bot.tree.command(name="files", description="Show available report commands.")
async def files_command(interaction: discord.Interaction):
    names = ", ".join(f"/{name}" for name in sorted(AVAILABLE_REPORTS.keys()))
    await interaction.response.send_message(f"Available reports: {names}")

# =========================================================
# REPORT COMMANDS
# =========================================================

@bot.tree.command(name="mlb", description="Generate and show the latest MLB report.")
async def mlb_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await generate_and_send_report(interaction, "mlb")


@bot.tree.command(name="nba", description="Generate and show the latest NBA report.")
async def nba_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await generate_and_send_report(interaction, "nba")


@bot.tree.command(name="nhl", description="Generate and show the latest NHL report.")
async def nhl_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await generate_and_send_report(interaction, "nhl")


@bot.tree.command(name="nfl", description="Generate and show the latest NFL report.")
async def nfl_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await generate_and_send_report(interaction, "nfl")


@bot.tree.command(name="soccer", description="Generate and show the latest soccer report.")
async def soccer_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await generate_and_send_report(interaction, "soccer")


@bot.tree.command(name="global", description="Generate and show the latest global sports report.")
async def global_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await generate_and_send_report(interaction, "global")


@bot.tree.command(name="fantasy", description="Generate and show the latest fantasy report.")
async def fantasy_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await generate_and_send_report(interaction, "fantasy")


@bot.tree.command(name="ncaafb", description="Generate and show the latest NCAAFB report.")
async def ncaafb_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await generate_and_send_report(interaction, "ncaafb")


@bot.tree.command(name="betting", description="Generate and show the latest betting report.")
async def betting_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    await generate_and_send_report(interaction, "betting")

# =========================================================
# PREFIX COMMANDS (OPTIONAL)
# =========================================================

@bot.command(name="ping")
async def ping_prefix(ctx):
    await ctx.send("🏓 Pong!")


@bot.command(name="files")
async def files_prefix(ctx):
    names = ", ".join(f"!{name}" for name in sorted(AVAILABLE_REPORTS.keys()))
    await ctx.send(f"Available prefix reports: {names}")

# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    print("Token loaded:", bool(DISCORD_TOKEN))
    print("Guild loaded:", bool(DISCORD_GUILD_ID))
    print("Token preview:", DISCORD_TOKEN[:10] + "..." if DISCORD_TOKEN else "None")
    bot.run(DISCORD_TOKEN)