import logging
import os
import random
from functools import lru_cache

import discord
from discord import Status
from discord.ext import commands

from discord.ext.commands import Context

import db
import core

admin = os.environ['DISCORD_ADMIN']
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)


# TODO: change to LRU or remove
@lru_cache(maxsize=1000)
def did_to_member(did):
    logging.info(f'cache for {did}')
    return {m.id: m for m in bot.get_all_members()}


def _status(ctx, did):
    try:
        return did_to_member(ctx.message.author.id).get(did).status
    except:
        return Status.offline if did % 2 else Status.online


@bot.event
async def on_command_error(ctx: Context, error):
    logging.error(error)
    command = ctx.command
    await ctx.send(f'This is not how you use {command}. Trying to get help...')
    await ctx.send_help(ctx.command)


# make decorator
async def protected(ctx):
    if not str(ctx.message.author) == admin:
        await ctx.send('only reut is allowed to do that!')
        raise Exception('not allowed')


def suggestion_str(ctx, discord_id, mmr):
    positions = db.get_positions(discord_id)
    return f"suggesting <@{discord_id}> [{_status(ctx, discord_id)}] [mmr: {mmr}), positions: {','.join(map(str, positions))}]"


@bot.command(brief='Register to party finder with your mmr. You will be assigned all positions.',
             description='Register to party finder with your mmr. You will be assigned all positions. '
                         'See `!help` for changing positions or updating mmr as you descend into herald ' )
async def register(ctx, mmr):
    discord_id = ctx.message.author.id
    core.init_user(discord_id, mmr)
    await ctx.send(f'registered {discord_id} with mmr of {mmr} mmr. Use `!set_mmr <mmr>` if incorrect.')


@bot.command(brief='Suggest players to party with',
             description='Suggests players to play with based on mmr difference (optional, default 1000) and position')
async def suggest(ctx, mmr_diff=1000):
    discord_id = ctx.message.author.id
    if not db.get_mmr(discord_id):
        await ctx.send('please !register first')
        return
    suggestions = [(did, mmr) for did, mmr in core.relevant_players(discord_id, mmr_diff) if _status(ctx,did) == Status.online]
    if not suggestions:
        await ctx.send('could not find suggestions :(')
        return
    await ctx.send(f'suggesting {len(suggestions)} players in private')
    suggestion_strs = [suggestion_str(ctx, discord_id, mmr) for discord_id, mmr in suggestions]
    await ctx.message.author.send('\n'.join(suggestion_strs))


@bot.command(brief='Show all registered players',
             description='show all registered players',
             hidden=True )
async def players(ctx):
    await protected(ctx)
    await ctx.send('sending players in private')
    await ctx.message.author.send('\n'.join(f'did: {did} - mmr: {mmr}, status: {_status(ctx, did)}' for did, mmr in db.players()))


@bot.command(brief='Show your mmr',
             description='Show your mmr. Update with `!set_mmr`')
async def mmr(ctx):
    mmr = db.get_mmr(ctx.message.author.id)
    await ctx.send(f'mmr: {mmr}')


@bot.command(brief='Set your mmr',
             description='Set your mmr. Show with `!get_mmr`')
async def set_mmr(ctx, new_mmr: int):
    old_mmr = core.update_mmr(ctx.message.author.id, new_mmr)
    await ctx.send(f'mmr set {old_mmr} -> {new_mmr}')


@bot.command(brief='Add position.',
             description='Add a position you play. Show current positions using `!positions`. Remove with `!remove_position`')
async def add_position(ctx, new_position: int):
    discord_id = ctx.message.author.id
    old_positions = db.get_positions(discord_id)
    db.add_position(discord_id, new_position)
    new_positions = db.get_positions(discord_id)
    await ctx.send(f'positions set {old_positions} -> {new_positions}')


@bot.command(brief='Remove a position you no longer play',
             description='Remove a position you no longer play. See current positions with `!positions`. Add with `!add_position`')
async def remove_position(ctx, position: int):
    discord_id = ctx.message.author.id
    old_positions = db.get_positions(discord_id)
    db.remove_position(discord_id, position)
    new_positions = db.get_positions(discord_id)
    await ctx.send(f'positions set {old_positions} -> {new_positions}')


@bot.command(brief='Get your current positions',
             description='Get your current positions. Add with `!add_position`, remove with `!remove_position`')
async def positions(ctx,):
    discord_id = ctx.message.author.id
    positions = db.get_positions(discord_id)
    await ctx.send(f'positions: {positions}')


@bot.command(brief='Remove from party finder',
             description='Remove yourself from party finder')
async def remove(ctx):
    discord_id = ctx.message.author.id
    db.delete_player(discord_id)
    await ctx.send('removed from party finder')


@bot.command(brief='back up db',
             description='backup db',
             hidden=True)
async def backup(ctx):
    await protected(ctx)
    response = core.backup()
    await ctx.send(response)


@bot.command(brief='fake register',
             description='fakse register',
             hidden=True)
async def fake(ctx, mmr):
    await protected(ctx)
    discord_id = random.randint(-999999, -1)
    core.init_user(discord_id, mmr)
    await ctx.send(f'registered {discord_id} with mmr of {mmr} mmr. Use `!set_mmr <mmr>` if incorrect.')


@bot.command(brief='restore back up',
             description='restore backup db',
             hidden=True)
async def restore(ctx, bkp):
    await protected(ctx)
    response = core.restore(bkp)
    await ctx.send(response)


@bot.command(brief='list backup',
             description='list backups',
             hidden=True)
async def backups(ctx):
    await protected(ctx)
    bkps = core.backups()
    for bkp in sorted(bkps, reverse=True):
        await ctx.send(bkp)

if __name__ == "__main__":
    bot.run(os.environ['DISCORD_TOKEN'])
