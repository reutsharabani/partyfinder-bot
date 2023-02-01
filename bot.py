import functools
import logging
import os
import random

import discord
from discord import Status, app_commands
from discord.ext import commands

import db
import s3

admin = os.environ['DISCORD_ADMIN']
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)


def _status(did_to_member, did):
    # noinspection PyBroadException
    try:
        return did_to_member.get(did).status
    except Exception:
        return Status.offline if did % 2 else Status.online


# make decorator
def protected(coro):
    # hope first arg is ctx
    @functools.wraps(coro)
    async def wrapper(ctx, *args, **kwargs):
        logging.error('trying to run protected command')
        if not str(ctx.message.author) == admin:
            await ctx.send(f"only {admin} is allowed to do that!")
            raise Exception('not allowed')
        logging.error('running protected command')
        return await coro(ctx, *args, **kwargs)

    return wrapper


@bot.command(brief='Register to party finder with your mmr. '
                   'If you don\'t specify positions you will be assigned all positions.',
             description='Register to party finder with your mmr. You will be assigned all positions. '
                         'See `!help` for changing positions or updating mmr as you descend into herald. '
                         '`!register 1337 4,5` will register you as a pos 4 or 5 player with mmr of 1337')
async def register(ctx,
                   mmr: int = commands.parameter(description='your mmr'),
                   positions: str = commands.parameter(default='1,2,3,4,5',
                                                       description='positions you play (defaults to all positions)')):
    positions = positions or '1,2,3,4,5'
    positions = (set(map(int, positions.split(','))) & {1, 2, 3, 4, 5})
    discord_id = ctx.message.author.id
    db.register(discord_id, mmr, positions=positions)
    await ctx.send(f'registered {discord_id} with mmr of {mmr} mmr and positions {positions}. '
                   f'Use `!set_mmr <mmr>` if incorrect.')


@bot.command(brief='Suggest players to party with',
             description='Suggests players to play with based on mmr difference (optional, default 1000) and position')
async def suggest(ctx,
                  mmr_diff: int = commands.parameter(default=1000,
                                                     description='max mmr difference between you and suggestions'),
                  max_suggestions: int = commands.parameter(default=5,
                                                            description='max suggestions (max 20)')):
    discord_id = ctx.message.author.id
    if not db.get_mmr(discord_id):
        await ctx.send('please !register first')
        return
    did_to_member = {m.id: m for m in bot.get_all_members()}
    suggestions = [(did, mmr) for did, mmr in db.relevant_players(discord_id, mmr_diff, min(20, max_suggestions)) if
                   _status(did_to_member, did) == Status.online]
    if not suggestions:
        await ctx.send('could not find suggestions :(')
        return

    template = '{: <20}| {: <7}| {: <10}'
    mentions = ' | '.join(f'<@{discord_id}> [{mmr}]' for discord_id, mmr in suggestions)
    table_sep = '```'
    headers = template.format('Discord Id', 'MMR', 'Status')
    separator = '-' * len(headers)
    table = '\n'.join(template.format(did, mmr, str(_status(did_to_member, did))) for did, mmr in suggestions)
    await ctx.send('\n'.join([mentions, table_sep, headers, separator, table, table_sep]))


@bot.command(brief='Show all registered players',
             description='show all registered players',
             hidden=True)
@protected
async def players(ctx):
    template = '{: <25}| {: <8}| {: <10}| {: <20}'
    table_sep = '```'
    headers = template.format('Discord ID', 'MMR', 'Status', 'Positions')
    separator = '-' * len(headers)
    did_to_member = {m.id: m for m in bot.get_all_members()}
    table = '\n'.join(template.format(f'{did}',
                                      f'{mmr}',
                                      f'{_status(did_to_member, did)}',
                                      f'{db.get_positions(did)}')
                      for did, mmr in db.players())
    await ctx.message.author.send(
        '\n'.join([table_sep,
                   headers,
                   separator,
                   table,
                   table_sep]))


@bot.command(brief='Show your mmr',
             name='mmr',
             description='Show your mmr. Update with `!set_mmr`')
async def get_mmr(ctx):
    discord_id = ctx.message.author.id
    mmr = db.get_mmr(discord_id)
    await ctx.send(f'mmr: {mmr}')


@bot.command(brief='Set your mmr',
             description='Set your mmr. Show with `!get_mmr`')
async def set_mmr(ctx, new_mmr: int = commands.parameter(description='new mmr to set')):
    discord_id = ctx.message.author.id
    old_mmr = db.get_mmr(discord_id)
    db.update_mmr(discord_id, new_mmr)
    await ctx.send(f'mmr set {old_mmr} -> {new_mmr}')


@bot.command(brief='Set positions you play',
             description='Set the positions you play.'
                         'Show current positions using `!positions`.')
async def set_positions(ctx,
                        new_positions: str = commands.parameter(default='1,2,3,4,5',
                                                                description='positions to set')):
    new_positions = set(map(int, new_positions.split(',')))
    discord_id = ctx.message.author.id
    old_positions = db.get_positions(discord_id)
    db.set_positions(discord_id, new_positions)
    await ctx.send(f'positions set {old_positions} -> {new_positions}')


@bot.command(brief='Get your current positions',
             name='positions',
             description='Get your current positions. Add with `!add_position`, remove with `!remove_position`')
async def get_positions(ctx):
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
@protected
async def backup(ctx):
    response = s3.backup()
    await ctx.send(response)


@bot.command(brief='fake register',
             description='fake register',
             hidden=True)
@protected
async def fake(ctx,
               mmr: int = commands.parameter(description='mmr to set'),
               positions: str = commands.parameter(description='positions to set (e.g. 4,5)')):
    positions = (set(map(int, positions)) & {1, 2, 3, 4, 5}) or {1, 2, 3, 4, 5}
    discord_id = random.randint(-999999, -1)
    db.register(discord_id, mmr, positions)
    await ctx.send(f'registered {discord_id} with mmr of {mmr} mmr with positions {1, 2, 3, 4, 5}. '
                   f'Use `!set_mmr <mmr>` if incorrect.')


@bot.command(brief='restore back up',
             description='restore backup db',
             hidden=True)
@protected
async def restore(ctx,
                  bkp: str = commands.parameter(description='backup name')):
    response = s3.restore(bkp)
    await ctx.send(response)


@bot.command(brief='list backup',
             description='list backups',
             hidden=True)
@protected
async def backups(ctx):
    bkps = s3.backups()
    await ctx.send('\n'.join(sorted(bkps, reverse=True)))


if __name__ == "__main__":
    bot.run(os.environ['DISCORD_TOKEN'])
