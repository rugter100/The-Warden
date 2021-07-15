import discord
import mysql.connector
import yaml
import sys
import os
import shutil
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get
from mcuuid import MCUUID
from mcuuid.tools import is_valid_minecraft_username, is_valid_mojang_uuid

intents = discord.Intents(guilds=True, messages=True, dm_messages=True, members=True, voice_states=True)
bot = commands.Bot(command_prefix='>', intents=intents)

with open(r'config.yml') as config:
    cfg = yaml.load(config, Loader=yaml.FullLoader)
    db = mysql.connector.connect(
        host=cfg['Database']['Host'],
        user=cfg['Database']['Username'],
        password=cfg['Database']['Password'],
        database=cfg['Database']['DatabaseName']
    )
    cursor = db.cursor(buffered=True)

if cfg['Bottoken'] == '':
    print('[ERROR] Bot Token not configured Correctly!')
    sys.exit()
else:
    print('[INFO] Bot token Found! Using Configured token')

if cfg['RunSetup'] == 1:  # Bot initialization
    print('[WARN] Bot not set up. Running initialization')
    print('[WARN] This will delete ALL tables used by the bot in the database!')
    confirm = input('[INFO] Please type YES if you want to continue and NO if you only want to generate new databases: ')
    if confirm == 'YES':
        cursor.execute('DROP TABLE IF EXISTS {}serversettings'.format(cfg['Database']['Prefix']))
        cursor.execute('DROP TABLE IF EXISTS {}guilds'.format(cfg['Database']['Prefix']))
        cursor.execute('DROP TABLE IF EXISTS {}userinfo'.format(cfg['Database']['Prefix']))
        shutil.rmtree("Botdata")
        print('[INFO] Databases and config files have been reset!')
    if not os.path.exists('BotData'):
        os.mkdir('BotData')
    if not os.path.exists('BotData/Users'):
        os.mkdir('BotData/Users')
    if not os.path.exists('BotData/Guilds'):
        os.mkdir('BotData/Guilds')
    cursor.execute('CREATE TABLE IF NOT EXISTS {}serversettings (serverid int AUTO_INCREMENT NOT NULL PRIMARY KEY,initialized boolean,dcserverid bigint,mcserverip varchar(36))'.format(cfg['Database']['Prefix']))
    cursor.execute('CREATE TABLE IF NOT EXISTS {}guilds (serverid int,guildid int AUTO_INCREMENT NOT NULL PRIMARY KEY,guildcolor varchar(6),guildname varchar(36),guildleaderid int,bankname varchar(36))'.format(cfg['Database']['Prefix']))
    # cursor.execute('CREATE TABLE IF NOT EXISTS {}currencies (serverid int,guildid int,currencyid int AUTO_INCREMENT NOT NULL PRIMARY KEY,currencyname varchar(16),bankerid int)'.format(cfg['Database']['Prefix']))
    cursor.execute('CREATE TABLE IF NOT EXISTS {}userinfo (serverid int,userid int AUTO_INCREMENT NOT NULL PRIMARY KEY,dcuserid bigint,mcuserid varchar(33),firstname varchar(36),lastname varchar(36),age int(4),race varchar(36),guildid int,job varchar(36),nickname varchar(36))'.format(cfg['Database']['Prefix']))
    db.commit()


@bot.event
async def on_ready():
    print('[INFO] Logged in as {0.user}'.format(bot))
    print('[INFO] Currently in {}'.format(bot.guilds))


@bot.event
async def on_guild_leave(guild: discord.Guild):
    print('[INFO] Left guild {0.name}'.format(guild))


@bot.command()
async def helpme(ctx, arg1=None):
    if arg1 == 'Botowner':
        await ctx.send('OwnerID help!'
                       'Command syntaxes:'
                       '\n`<>` = Required'
                       '\n`{}` = Optional'
                       '\n`[]` = Multiple options seperated by `/`'
                       '\n\nProfile commands:'
                       '\n - `makeprofile <discorduserid> <mcusername> <firstname> <lastname> <age> <race> {job} {nickname}`'
                       '\n - `editprofile [username/firstname/lastname/age/race/job/nickname] <new value> <@user>`'
                       '\n - `makeguild <guildname> <guildcolor (example: 080808)> <bankname> <@guildleader>`'
                       '\n - `editguild <guildname> [color/name/leader/bankname] <value>`'
                       '\n - `deleteguild <guildname>`'
                       '\n - `addmember <@user> <guildname>`'
                       '\n - `removemember <@user> <guildname>`')
    elif arg1 == 'Admin':
        await ctx.send('Command syntaxes:'
                       '\n`<>` = Required'
                       '\n`{}` = Optional'
                       '\n`[]` = Multiple options seperated by `/`'
                       '\n\nAdmin Commands:'
                       '\n - `initialize <serverip>`'
                       '\n - `serveredit [mcserverip] <value>`')
    else:
        await ctx.send('Command syntaxes:'
                       '\n`<>` = Required'
                       '\n`{}` = Optional'
                       '\n`[]` = Multiple options seperated by `/`'
                       '\n\nUser Commands:'
                       '\n - `profile {@user}`'
                       '\n - `makeprofile <mcusername> <firstname> <lastname> <age> <race> {job} {nickname}`'
                       '\n - `editprofile [username/firstname/lastname/age/race/job/nickname] <new value>`'
                       '\n - `listmembers`'
                       '\n - `makeguild <guildname> <guildcolor (example: 080808)> {bankname}`'
                       '\n - `editguild [color/name/leader/bankname] <value>`'
                       '\n - `guildinfo <guildname>`'
                       '\n - `listguilds`'
                       '\n - `guildmembers <guildname>`'
                       '\n\n Guild leader commands:'
                       '\n - `addmember <@user>`')



@bot.command()
@commands.has_permissions(administrator=True)
async def initialize(ctx, arg1=None):
    cursor.execute('SELECT * FROM serversettings WHERE dcserverid=%s AND initialized=0',
                   (ctx.guild.id,))
    initialized = cursor.rowcount
    data = cursor.fetchall()
    if initialized == 0:
        if arg1 == None:
            await ctx.send('Missing parameters! Please use `initialize <serverip>`')
        else:
            cursor.execute('INSERT INTO serversettings (initialized,dcserverid,mcserverip) VALUES (1,%s,%s)',
                           (ctx.guild.id, arg1,))
            db.commit()
            cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
            serveridraw = cursor.fetchone()
            serverid = serveridraw[0]
            os.mkdir(f'BotData/Users/{serverid}')
            os.mkdir(f'BotData/Guilds/{serverid}')
            await ctx.send(f'Initialized server with dcserverid: `{ctx.guild}` and mcserverip: `{arg1}`')
    else:
        serverid = data[0]
        serverip = data[3]
        await ctx.send(f'Your server has already been initialized with serverid: `{serverid} and IP: `{serverip}``! Please use the `serveredit` command to edit your server settings')


@bot.command()
@commands.has_permissions(administrator=True)
async def serveredit(ctx, arg1=None, arg2=None):
    if arg1 == 'mcserverip':
        newip = arg2
        cursor.execute('SELECT mcserverip FROM serversettings WHERE dcserverid=%s',
                       (ctx.guild.id,))
        oldipraw = cursor.fetchone()
        oldip = oldipraw[0]
        cursor.execute('UPDATE serversettings SET mcserverip=%s WHERE dcserverid=%s',
                       (newip, ctx.guild.id,))
        db.commit()
        await ctx.send(f'Changed the server IP from `{oldip}` to `{newip}`')
    else:
        await ctx.send('Missing or wrong parameters!\nPlease use `serveredit <param> <value>`! Possible Parameters to edit:\n - mcserverip')


@bot.command(name="profile")
async def profile(ctx, user: discord.User=None):
    if user:
        dcuserid = user.id
    else:
        dcuserid = ctx.message.author.id
    cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
    serveridraw = cursor.fetchone()
    serverid = serveridraw[0]
    cursor.execute('SELECT * FROM userinfo WHERE dcuserid=%s AND serverid=%s', (dcuserid, serverid,))
    userdata = cursor.fetchone()
    firstname = userdata[4]
    lastname = userdata[5]
    age = userdata[6]
    race = userdata[7]
    guildid = userdata[8]
    if guildid != None:
        cursor.execute('SELECT guildname,guildcolor FROM guilds WHERE serverid=%s AND guildid=%s', (serverid, guildid,))
        guilddata = cursor.fetchone()
        guildname = guilddata[0]
        guildcolor = guilddata[1]
        guildcolorhex = int(guildcolor, 16)
        guildvalue = f'{guildname} Guild'
    else:
        guildcolorhex = 0x808080
        guildvalue = 'Lone wolf. Adventurer!'
    job = userdata[9]
    nickname = userdata[10]
    embed = discord.Embed(title=f'{firstname} {lastname}''s Profile', color=guildcolorhex)
    embed.add_field(name='Nickname', value=nickname, inline=False)
    embed.add_field(name='Age', value=f'{age} Years old')
    embed.add_field(name='Race', value=race)
    embed.add_field(name='Guild', value=guildvalue, inline=False)
    embed.add_field(name='Job', value=job, inline=False)
    embed.set_footer(text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
    await ctx.send(embed=embed)


@profile.error
async def profile_error(ctx):
    await ctx.send('Invalid user! Please mention the user!')


# Has ownerid Command
@bot.command()
async def makeprofile(ctx, arg1=None, arg2=None, arg3=None, arg4=None, arg5=None, arg6=None, arg7=None, arg8=None):
    error = False
    embederror = discord.Embed(title='We found errors in your command syntax!', color=0xF66946)
    if arg1.isdigit():
        if ctx.author.id == int(cfg['Botownerid']):
            dcuser = arg1
            mcusername = arg2
            firstname = arg3
            lastname = arg4
            agestr = arg5
            age = 0
            if agestr is not None:
                if agestr.isdigit():
                    age = int(arg5)
            race = arg6
            job = arg7
            nickname = arg8
        else:
            error = True
            embederror.add_field(name='Insufficient Privileges!', value='You do not have the permission to make profiles for other users!')
    else:
        dcuser = ctx.author
        mcusername = arg1
        firstname = arg2
        lastname = arg3
        agestr = arg4
        age = 0
        if agestr is not None:
            if agestr.isdigit():
                age = int(arg4)
        race = arg5
        job = arg6
        nickname = arg7
    if None in (mcusername, firstname, lastname, age, race):
        await ctx.send('Missing or wrong parameters!\nPlease use `makeprofile <mcusername> <firstname> <lastname> <age> <race> {job} {nickname}`\n**Remember! If a name has spaces put it in between ""**')
    else:
        cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
        serveridraw = cursor.fetchone()
        serverid = serveridraw[0]
        if not is_valid_minecraft_username(mcusername):
            embederror.add_field(name='Invalid username!', value=f'`{mcusername}` is not a valid minecraft username. Remember this is case sensitive!')
            error = True
        if not agestr.isdigit():
            embederror.add_field(name='Age is not only digits!', value=f'`{agestr}` is not a valid age! Please use only numbers!')
            error = True
        elif len(str(age)) > 4:
            embederror.add_field(name='You want to be too old for us!', value=f'`{age}` is really too old... You dont have to be older than 9999 years old...')
            error = True
        if len(firstname) > 36:
            embederror.add_field(name='Your first name is too long!', value=f'`{firstname}` is too long of a name. Please use max 36 characters for your first name.')
            error = True
        if len(lastname) > 36:
            embederror.add_field(name='Your last name is too long!', value=f'`{lastname}` is too long of a name. Please use max 36 characters for your last name.')
            error = True
        if len(race) > 36:
            embederror.add_field(name='The name of your race is too long!', value=f'`{race}` is too long of a name for a race. Please use max 36 characters for your race.')
            error = True
        if job is not None:
            if len(job) > 36:
                embederror.add_field(name='The title of your job is too long!', value=f'The job title`{job}` is too long! Please use max 36 characters for your job title.')
                error = True
        if nickname is not None:
            if len(nickname) > 36:
                embederror.add_field(name='Your nickname is too long!', value=f'`{nickname}` is too long. Please use max 36 characters for your nickname.')
        cursor.execute('SELECT * FROM userinfo WHERE serverid=%s AND dcuserid=%s', (serverid, dcuser.id,))
        entryexists = cursor.rowcount
        if entryexists == 1:
            entrydata = cursor.fetchone()
            firstname = entrydata[4]
            lastname = entrydata[5]
            age = entrydata[6]
            race = entrydata[7]
            job = entrydata[8]
            guildid = entrydata[9]
            if guildid is not None:
                cursor.execute('SELECT guildname FROM guilds WHERE guildid=%s', (guildid,))
                guildnameraw = cursor.fetchone()
                guildname = guildnameraw[0]
            if job is None:
                jobstring = 'you are unemployed'
            else:
                jobstring = f'you work as a {job}'
            embederror.add_field(name=f'{firstname} {lastname}, You already have a profile!', value=f'You already have a profile! You are {firstname} {lastname}, you are {age} years old, a {race}, a part of the {guildname} and {jobstring}')
            error = True
        if entryexists > 1:
            embederror.add_field(name='CRITICAL ERROR!', value='Somehow we found more than one entry linked to your Userid! This is a big issue! Please contact Server admins!')
            error = True
        if error:
            await ctx.send(embed=embederror)
        else:
            mcuserid = MCUUID(name=mcusername)
            cursor.execute('INSERT INTO userinfo (serverid,dcuserid,mcuserid,firstname,lastname,age,race,job,nickname) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                           (serverid, dcuser.id, mcuserid.uuid, firstname, lastname, age, race, job, nickname,))
            db.commit()
            cursor.execute('SELECT userid FROM userinfo WHERE serverid=%s AND dcuserid=%s AND mcuserid=%s', (serverid, dcuser.id, mcuserid.uuid,))
            useridraw = cursor.fetchone()
            userid = useridraw[0]
            os.mkdir(f'BotData/Users/{serverid}/{userid}')
            embed = discord.Embed(title='Chacacter Created!', description=f'You are now {firstname} {lastname}', color=0x808080)
            embed.add_field(name='Age', value=f'{age} Years old')
            embed.add_field(name='Race', value=race)
            if job is not None:
                embed.add_field(name='Job', value=job)
            if nickname is not None:
                embed.add_field(name='Nickname', value=nickname)
            embed.set_footer(text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
            await ctx.send(embed=embed)


# Has ownerid Command
@bot.command()
async def editprofile(ctx, arg1=None, arg2=None, dcuser: discord.User=None):
    cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
    serverid = cursor.fetchone()[0]
    if dcuser is None:
        user = ctx.message.author
        define = True
    elif ctx.author.id == int(cfg['Botownerid']):
        user = dcuser
        define = True
    if define:
        cursor.execute('SELECT * FROM userinfo WHERE serverid=%s AND dcuserid=%s', (serverid, user.id,))
        userdata = cursor.fetchone()
        firstname = userdata[4]
        lastname = userdata[5]
        age = userdata[6]
        race = userdata[7]
        job = userdata[9]
        nickname = userdata[10]
    if userdata is not None:
        updatedb = False
        if arg1 == 'username':
            if is_valid_mojang_uuid(arg2):
                updatedb = True
                param1 = 'mcuserid'
                param2 = MCUUID(name=arg2)
                mcuserid = MCUUID(uuid=userdata[3])
                param3 = mcuserid.name
        elif arg1 == 'firstname':
            if len(arg2) < 37:
                updatedb = True
                param1 = 'firstname'
                param2 = arg2
                firstname = arg2
                param3 = userdata[4]
        elif arg1 == 'lastname':
            if len(arg2) < 37:
                updatedb = True
                param1 = 'lastname'
                param2 = arg2
                lastname = arg2
                param3 = userdata[5]
        elif arg1 == 'age':
            if len(arg2) < 5:
                if arg2.isdigit():
                    updatedb = True
                    param1 = 'age'
                    param2 = int(arg2)
                    age = arg2
                    param3 = userdata[6]
        elif arg1 == 'race':
            if len(arg2) < 37:
                updatedb = True
                param1 = 'race'
                param2 = arg2
                race = arg2
                param3 = userdata[7]
        elif arg1 == 'job':
            if len(arg2) < 37:
                updatedb = True
                param1 = 'job'
                param2 = arg2
                job = arg2
                param3 = userdata[9]
        elif arg1 == 'nickname':
            if len(arg2) < 37:
                updatedb = True
                param1 = 'nickname'
                param2 = arg2
                nickname = arg2
                param3 = userdata[10]
        if updatedb:
            message = await ctx.send(f'Are you sure you want to change your {arg1}?\nCurrent entry: `{param3}`\nNew entry: {arg2}\nPlease type `YES` to confirm, `NO` to cancel.')
            def check(m):
                return m.channel == ctx.channel
            msg = await bot.wait_for('message', check=check, timeout=500)
            checkcontinue = msg.content.lower()
            if checkcontinue == 'yes':
                await message.delete()
                await msg.delete()
                cursor.execute(f'UPDATE userinfo SET {param1}=%s WHERE serverid=%s AND userid=%s', (param2, serverid, userdata[1],))
                db.commit()
                if userdata[8] != None:
                    cursor.execute('SELECT guildname,guildcolor FROM guilds WHERE serverid=%s AND guildid=%s',(serverid, userdata[8],))
                    guilddata = cursor.fetchone()
                    guildname = guilddata[0]
                    guildcolorhex = int(guilddata[1], 16)
                    guildvalue = f'{guildname} Guild'
                else:
                    guildcolorhex = 0x808080
                    guildvalue = 'Lone wolf. Adventurer!'
                await ctx.send('Success! Your profile has been updated!')
                embed = discord.Embed(title=f'{firstname} {lastname}''s Profile', color=guildcolorhex)
                if nickname is not None:
                    embed.add_field(name='Nickname', value=nickname, inline=False)
                embed.add_field(name='Age', value=f'{age} Years old')
                embed.add_field(name='Race', value=race)
                embed.add_field(name='Guild', value=guildvalue, inline=False)
                embed.add_field(name='Job', value=job, inline=False)
                embed.set_footer(text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
                await ctx.send(embed=embed)
            else:
                await ctx.send('Command cancelled! Please rerun the command to give it another try!')
        else:
            await ctx.send(f'Unknown parameter or syntax! `{arg1}`. Command syntax:\n`editprofile [username/firstname/lastname/age/race/job/nickname] <new value>`\nRemember to use max 36 characters for names/titles and you cannot be older than 9999 years old!')
    else:
        await ctx.send('You dont have a character yet! Please use `makeprofile <mcusername> <firstname> <lastname> <age> <race> {job}` to create your character!')


@bot.command()
async def listmembers(ctx):
    cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
    serverid = cursor.fetchone()[0]
    cursor.execute('SELECT userid,firstname,lastname,age,race,guildid,job FROM userinfo WHERE serverid=%s', (serverid,))
    memberdata = cursor.fetchall()
    embedcount = 0
    pagecount = 0
    embed = discord.Embed(title='RP Member list', description=f'The RP has {cursor.rowcount} Characters')
    print('yes')
    for row in memberdata:
        cursor.execute('SELECT guildname,guildleaderid FROM guilds WHERE serverid=%s AND guildid=%s', (serverid, row[5],))
        guilddata = cursor.fetchone()
        guildname = guilddata[0]
        if guilddata[1] == row[0]:
            guildname = f'Leader of the {guilddata[0]}'
        embed.add_field(name=f'{row[1]} {row[2]}', value=f'Age: {row[3]} Race: {row[4]}\nGuild: {guildname} Guild\nJob: {row[6]}')
        embedcount += 1
        if embedcount == 25:
            pagecount += 1
            embed.set_footer(text='Requested by {} | Page {}/? | RP Bot Ver {}'.format(ctx.author.display_name, embedcount, cfg['Version']))
            await ctx.send(embed=embed)
    if pagecount == 0:
        embed.set_footer(text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
    else:
        embed.set_footer(text='Requested by {} | Page {}/? | RP Bot Ver {}'.format(ctx.author.display_name, embedcount, cfg['Version']))
    await ctx.send(embed=embed)

# ======================
# Guild related commands
# ======================


# Has ownerid Command
@bot.command()
async def makeguild(ctx, arg1=None, arg2=None, arg3=None, user: discord.User=None):
    runcmd = False
    guildname = arg1
    if arg2.startswith('#'):
        guildcolor = arg2.replace('#', '')
    else:
        guildcolor = arg2
    if user is None:
        guildleader = ctx.message.author
        runcmd = True
    else:
        if ctx.author.id == int(cfg['Botownerid']):
            guildleader = user
            runcmd = True
        else:
            await ctx.send('You must be the bot owner to make a guild for someone else!')
    bankname = arg3
    if runcmd:
        error = False
        if None in (guildname, guildcolor, guildleader):
            await ctx.send('Missing or wrong parameters!\nPlease use `makeguild <guildname> <guildcolor (example: 080808)> {bankname}`\n*Remember! If a name has spaces put it in between ""')
        else:
            embederror = discord.Embed(title='We found errors in your command!', color=0xF66946)
            cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
            serverid = cursor.fetchone()[0]
            cursor.execute('SELECT * FROM guilds WHERE serverid=%s AND guildname=%s', (serverid, guildname,))
            entyexists = cursor.rowcount
            if entyexists == 1:
                embederror.add_field(name='The guild name is already in use!', value=f'The guild name `{guildname}` is already in useby another guild!')
                error = True
            if len(guildname) > 36:
                embederror.add_field(name='Your guild name is too long!', value=f'`{guildname}` is too long of a name. Please use max 36 characters for your guild name.')
                error = True
            if len(guildcolor) != 6:
                embederror.add_field(name='Your colour hex is too long or short!', value=f'A colour hex should be exacty 6 characters long. `{guildcolor}` is either too long or too short')
                error = True
            cursor.execute('SELECT userid FROM userinfo WHERE serverid=%s AND dcuserid=%s', (serverid, user.id,))
            guildleaderidentry = cursor.rowcount
            if guildleaderidentry == 0:
                embederror.add_field(name='User was not found!', value=f'We could not find user {user.mention}. This probably means they dont have a character profile yet!')
                error = True
            else:
                guildleaderidraw = cursor.fetchone()
                guildleaderid = guildleaderidraw[0]
            if bankname is not None:
                if len(bankname) > 36:
                    embederror.add_field(name='Bank name too long', value=f'The bank name `{bankname}` is too long! Please use max 36 characters for the name of your bank.')
                    error = True
            if error:
                await ctx.send(embed=embederror)
            else:
                # Database Part
                cursor.execute('INSERT INTO guilds (serverid,guildname,guildcolor,guildleaderid,bankname) VALUES (%s,%s,%s,%s,%s)',
                               (serverid, guildname, guildcolor, guildleaderid, bankname,))
                cursor.execute('SELECT guildid FROM guilds WHERE serverid=%s AND guildcolor=%s AND guildname=%s AND guildleaderid=%s', (serverid, guildcolor, guildname, guildleaderid,))
                guildid = cursor.fetchone()[0]
                cursor.execute('UPDATE userinfo SET guildid=%s WHERE serverid=%s AND userid=%s AND dcuserid=%s', (guildid, serverid, guildleaderid, user.id,))
                db.commit()
                # File Part
                os.mkdir(f'BotData/Guilds/{serverid}/{guildid}')
                # Discord Part
                createrole = await ctx.guild.create_role(colour=int(guildcolor, 16), name=f'{guildname} Guild')
                createrole.hoist = True # TODO Add showing role seperately from others but idk how to fucking add that shit
                role = discord.utils.get(ctx.guild.roles, name=f'{guildname} Guild')
                await ctx.message.author.add_roles(role)
                # Discord Message
                embed = discord.Embed(title=f'{arg1} Guild Created!', color=int(guildcolor, 16))
                embed.add_field(name='Guild leader:', value=guildleader.mention)
                if bankname is not None:
                    embed.add_field(name='Bank name:', value=bankname)
                embed.set_footer(text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
                await ctx.send(embed=embed)


# Has ownerid Command
@bot.command()
async def editguild(ctx, arg1=None, arg2=None, arg3=None):
    if None not in (arg1, arg2):
        colorcmd = 'Color', 'color', 'Colour', 'colour'
        namecmd = 'name', 'Name'
        banknamecmd = 'bankname', 'Bankname', 'bank', 'Bank'
        cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
        serverid = cursor.fetchone()[0]
        cursor.execute('SELECT userid,firstname,lastname FROM userinfo WHERE serverid=%s AND dcuserid=%s', (serverid, ctx.message.author.id,))
        guildleaderdata = cursor.fetchone()
        if guildleaderdata is not None:
            print('YES2')
            print(colorcmd + namecmd + banknamecmd)
            guilddata = None
            if arg1 in (colorcmd + namecmd + banknamecmd):
                print('YES1')
                cursor.execute('SELECT guildcolor,guildname,bankname,guildid FROM guilds WHERE serverid=%s AND guildid=%s', (serverid, guildleaderdata[0],))
                guilddata = cursor.fetchone()
            elif ctx.author.id == int(cfg['Botownerid']):
                if arg2 in (colorcmd + namecmd + banknamecmd):
                    cursor.execute('SELECT guildcolor,guildname,bankname,guildid,guildleaderid FROM guilds WHERE serverid=%s AND guildname=%s', (serverid, arg1,))
                    guilddata = cursor.fetchone()
                    if guilddata is not None:
                        cursor.execute('SELECT userid,firstname,lastname FROM userinfo WHERE serverid=%s AND userid=%s', (serverid, guilddata[4],))
                        guildleaderdata = cursor.fetchone()
                        arg1 = arg2
                        arg2 = arg3
                    else:
                        await ctx.send(f'"{arg1} Guild" was not found!')
            if guilddata is not None:
                guildname = guilddata[1]
                guildcolor = int(guilddata[0], 16)
                bankname = guilddata[2]
                updatedb = False
                if arg1 in colorcmd:
                    if len(arg2) == 6:
                        param1 = 'guildcolor'
                        param2 = arg2
                        param3 = guilddata[0]
                        guildcolor = int(arg2, 16)
                        updatedb = True
                elif arg1 in namecmd:
                    if len(arg2) < 37:
                        param1 = 'guildname'
                        param2 = arg2
                        param3 = guilddata[1]
                        guildname = arg2
                        updatedb = True
                elif arg1 in banknamecmd:
                    if len(arg2) < 37:
                        param1 = 'bankname'
                        param2 = arg2
                        param3 = guilddata[2]
                        bankname = arg2
                        updatedb = True
                else:
                    await ctx.send(f'Unknown argument `{arg1}`. Please use the correct command syntax!\n`editguild [color/name/leader/bankname] <value>`')
                if updatedb:
                    message = await ctx.send(f'Are you sure you want to change your {arg1}?\nCurrent entry: `{param3}`\nNew entry: {arg2}\nPlease type `YES` to confirm, `NO` to cancel.')
                    def check(m):
                        return m.channel == ctx.channel
                    msg = await bot.wait_for('message', check=check, timeout=500)
                    checkcontinue = msg.content.lower()
                    if checkcontinue == 'yes':
                        await message.delete()
                        await msg.delete()
                        cursor.execute(f'UPDATE guilds SET {param1}=%s WHERE serverid=%s AND guildid=%s', (param2, serverid, guilddata[3],))
                        db.commit()
                    cursor.execute('SELECT userid FROM userinfo WHERE serverid=%s AND guildid=%s', (serverid, guilddata[3],))
                    guild_member_count = cursor.rowcount
                    if guild_member_count > 1:
                        members = 'Members'
                    else:
                        members = 'Member'
                    embed = discord.Embed(title=f'{guildname} Guild', description=f'`{guild_member_count}` {members}', color=guildcolor)
                    embed.add_field(name='Guild Leader', value=f'{guildleaderdata[1]} {guildleaderdata[2]}')
                    if guilddata[2] is not None:
                        embed.add_field(name='Bank information:', value=f'{guilddata[2]}')
                    embed.set_footer(
                        text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
                    await ctx.send(embed=embed)
                else:
                    await ctx.send('Command cancelled!')
            else:
                await ctx.send('You must be a guild leader to do this!')
        else:
            await ctx.send('please make a user profile before attempting to edit things!')
    else:
        await ctx.send('Please enter arguments in the command!\n`editguild [color/name/bankname] <value>`')


# Has ownerid Command
@bot.command()
async def deleteguild(ctx, arg1=None):
    cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
    serverid = cursor.fetchone()[0]
    cursor.execute('SELECT userid FROM userinfo WHERE serverid=%s AND dcuserid=%s', (serverid, ctx.message.author.id,))
    userid = cursor.fetchone()[0]
    if userid is not None:
        if arg1 is None:
            cursor.execute('SELECT guildname,guildid FROM guilds WHERE serverid=%s AND guildleaderid=%s', (serverid, userid,))
            guilddata = cursor.fetchone()
        elif ctx.author.id == int(cfg['Botownerid']):
            cursor.execute('SELECT guildname,guildid FROM guilds WHERE serverid=%s AND guildname=%s', (serverid, arg1,))
            guilddata = cursor.fetchone()
        else:
            await ctx.send("You do not have permission to delete someone else's guild! If you want to delete your own guild just do `deleteguild`. Remember you must be the guild leader to do this!")
        if guilddata is not None:
            message = await ctx.send(f'Are you ABSOLUTELY sure you want to delete the {guilddata[0]} Guild? This will delete all traces of the guild and you will NOT be able to revert this!\nPlease type `YES` to confirm, `NO` to cancel.')
            def check(m):
                return m.channel == ctx.channel
            msg = await bot.wait_for('message', check=check, timeout=500)
            checkcontinue = msg.content.lower()
            if checkcontinue == 'yes':
                await message.delete()
                await msg.delete()
                role = discord.utils.get(ctx.message.guild.roles, name=f'{guilddata[0]} Guild')
                if role is not None:
                    await role.delete()
                cursor.execute('DELETE FROM guilds WHERE serverid=%s AND guildid=%s AND guildname=%s AND guildleaderid=%s', (serverid, guilddata[1], guilddata[0], userid,))
                cursor.execute('UPDATE userinfo SET guildid=%s WHERE serverid=%s AND guildid=%s', (None, serverid, guilddata[1],))
                await ctx.send(f'The {guilddata[0]} Guild has vanished')
        elif ctx.author.id == int(cfg['Botownerid']):
            await ctx.send(f'{arg1} Guild was not found!')
        else:
            await ctx.send('You cant delete a guild if you are not the guild leader!')
    else:
        await ctx.send('You must have a profile to do anything!')


# Has ownerid Command
@bot.command()
async def addmember(ctx, dcuser: discord.Member=None, arg1=None):
    # Get server ID
    cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
    serverid = cursor.fetchone()[0]
    if arg1 is None:
        # Get userid from message author to check if they are a guild leader
        cursor.execute('SELECT userid FROM userinfo WHERE serverid=%s AND dcuserid=%s', (serverid, ctx.message.author.id,))
        guild_leader_id = cursor.fetchone()[0]
        # Check guilds database to see if the message author is leader of a guild
        cursor.execute('SELECT guildid,guildcolor,guildname FROM guilds WHERE serverid=%s AND guildleaderid=%s', (serverid, guild_leader_id,))
        guilddata = cursor.fetchone()
    elif arg1 is not None:
        if ctx.author.id == int(cfg['Botownerid']):
            cursor.execute('SELECT guildid,guildcolor,guildname FROM guilds WHERE serverid=%s AND guildname=%s', (serverid, arg1,))
            guilddata = cursor.fetchone()
    # If statement to decide what to do determined by the fact of whether they are a guild leader or not
    if guilddata is not None:
        # Get user data for member that is being added to the guild
        cursor.execute('SELECT userid,firstname,lastname,guildid FROM userinfo WHERE serverid=%s AND dcuserid=%s', (serverid, dcuser.id,))
        userdata = cursor.fetchone()
        if userdata is not None:
            # Check if user is already in guild or not
            if userdata[3] == guilddata[0]:
                await ctx.send('This user is already a part of your guild!')
            else:
                # update database entry to have guild id in userinfo
                cursor.execute('UPDATE userinfo SET guildid=%s WHERE serverid=%s AND userid=%s AND dcuserid=%s', (guilddata[0], serverid, userdata[0], dcuser.id,))
                db.commit()
                # Get list of total guild members
                cursor.execute('SELECT * FROM userinfo WHERE serverid=%s AND guildid=%s', (serverid, guilddata[0],))
                guild_member_count = cursor.rowcount
                role = discord.utils.get(ctx.guild.roles, name=f'{guilddata[2]} Guild')
                await dcuser.add_roles(role)
                # Message back to the user
                embed = discord.Embed(title='Success!', description=f'the {guilddata[2]} Guild now has {guild_member_count} Members!', color=int(guilddata[1], 16))
                embed.add_field(name=f'{userdata[1]} {userdata[2]} Joined the guild!', value='~Welcome~')
                embed.set_footer(text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
                await ctx.send(embed=embed)
        else:
            await ctx.send('This user doesnt have a profile!')
    elif ctx.author.id == int(cfg['Botownerid']):
        await ctx.send(f'{arg1} Guild was not found!')
    else:
        await ctx.send('You are either not the guild leader or you are not a part of a guild! Only the guild leader can assign new members!')


# Has ownerid Command
@bot.command()
async def removemember(ctx, dcuser: discord.Member=None, arg1=None):
    # Get server ID
    cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
    serverid = cursor.fetchone()[0]
    if arg1 is None:
        # Get userid from message author to check if they are a guild leader
        cursor.execute('SELECT userid FROM userinfo WHERE serverid=%s AND dcuserid=%s', (serverid, ctx.message.author.id,))
        guild_leader_id = cursor.fetchone()[0]
        # Check guilds database to see if the message author is leader of a guild
        cursor.execute('SELECT guildid,guildcolor,guildname FROM guilds WHERE serverid=%s AND guildleaderid=%s', (serverid, guild_leader_id,))
        guilddata = cursor.fetchone()
    elif arg1 is not None:
        if ctx.author.id == int(cfg['Botownerid']):
            cursor.execute('SELECT guildid,guildcolor,guildname FROM guilds WHERE serverid=%s AND guildname=%s',
                           (serverid, arg1,))
            guilddata = cursor.fetchone()
    # If statement to decide what to do determined by the fact of whether they are a guild leader or not
    if guilddata is not None:
        # Get user data for member that is being added to the guild
        cursor.execute('SELECT userid,firstname,lastname,guildid FROM userinfo WHERE serverid=%s AND dcuserid=%s', (serverid, dcuser.id,))
        userdata = cursor.fetchone()
        if userdata is not None:
            # Check if user is already in guild or not
            if userdata[3] == guilddata[0]:
                # update database entry to remove guild id in userinfo
                cursor.execute('UPDATE userinfo SET guildid=NULL WHERE serverid=%s AND userid=%s AND dcuserid=%s', (serverid, userdata[0], dcuser.id,))
                db.commit()
                # Get list of total guild members
                cursor.execute('SELECT * FROM userinfo WHERE serverid=%s AND guildid=%s', (serverid, guilddata[0],))
                guild_member_count = cursor.rowcount
                role = discord.utils.get(ctx.guild.roles, name=f'{guilddata[2]} Guild')
                await dcuser.remove_roles(role)
                # Message back to the user
                embed = discord.Embed(title='Success!', description=f'the {guilddata[2]} Guild now has {guild_member_count} Members!', color=int(guilddata[1], 16))
                embed.add_field(name=f'{userdata[1]} {userdata[2]} Joined the guild!', value='~Welcome~')
                embed.set_footer(text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
                await ctx.send(embed=embed)
            else:
                await ctx.send('This user is not a part of your guild!')
        else:
            await ctx.send('This user doesnt have a profile!')
    elif ctx.author.id == int(cfg['Botownerid']):
        await ctx.send(f'{arg1} Guild was not found!')
    else:
        await ctx.send('You are either not the guild leader or you are not a part of a guild! Only the guild leader can assign new members!')


@bot.command()
async def guildinfo(ctx, arg1=None):
    guildname = arg1
    if guildname is None:
        await ctx.send('Please enter a guildname without ''guild'' behind it!\n`guildinfo <guildname>`')
    else:
        cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
        serverid = cursor.fetchone()[0]
        cursor.execute('SELECT * FROM guilds WHERE serverid=%s AND guildname=%s', (serverid, guildname,))
        guilddata = cursor.fetchone()
        if guilddata is not None:
            guild_id = guilddata[1]
            guild_colorhex = int(guilddata[2], 16)
            guild_name = guilddata[3]
            guild_leaderid = guilddata[4]
            guild_bankname = guilddata[5]
            cursor.execute('SELECT * FROM userinfo WHERE serverid=%s AND userid=%s', (serverid, guild_leaderid,))
            guildleaderdata = cursor.fetchone()
            guild_ldr_dcuser = bot.get_user(guildleaderdata[2])
            guild_ldr_mcuser = MCUUID(uuid=guildleaderdata[3])
            guild_ldr_firstname = guildleaderdata[4]
            guild_ldr_lastname = guildleaderdata[5]
            cursor.execute('SELECT * FROM userinfo WHERE serverid=%s AND guildid=%s', (serverid, guild_id,))
            guild_member_count = cursor.rowcount
            if guild_member_count > 1:
                members = 'Members'
            else:
                members = 'Member'
            embed = discord.Embed(title=f'{guild_name} Guild', description=f'`{guild_member_count}` {members}', color=guild_colorhex)
            embed.add_field(name='Guild Leader', value=f'{guild_ldr_firstname} {guild_ldr_lastname}\nDiscord: {guild_ldr_dcuser}\nMinecraft: {guild_ldr_mcuser.name}')
            if guild_bankname is not None:
                embed.add_field(name='Bank information:', value=f'{guild_bankname}')
            embed.set_footer(text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
            await ctx.send(embed=embed)
        else:
            await ctx.send('Guild was not found! The name is case sensitive!')


@bot.command()
async def listguilds(ctx):
    cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
    serverid = cursor.fetchone()[0]
    cursor.execute('SELECT * FROM guilds WHERE serverid=%s', (serverid,))
    guilddata = cursor.fetchall()
    guilds = cursor.rowcount
    cursor.execute('SELECT userid FROM userinfo WHERE serverid=%s', (serverid,))
    membercount = cursor.rowcount
    embed = discord.Embed(title=f'the {ctx.guild.name} guilds!', description=f'The RP server has {guilds} Guilds and {membercount} Characters!')
    guildembeds = 0
    pagecount = 0
    for row in guilddata:
        guildcolor = row[2]
        guildname = row[3]
        guildleaderid = row[4]
        bankname = row[5]
        if bankname is not None:
            bankname = f'\nBank: {row[5]}'
        else:
            bankname = ''
        cursor.execute('SELECT userid,firstname,lastname FROM userinfo WHERE serverid=%s AND guildid=%s',(serverid, row[1],))
        guildmembers = cursor.rowcount
        memberdata = cursor.fetchall()
        for row in memberdata:
            if row[0] == guildleaderid:
                leaderfirstname = row[1]
                leaderlastname = row[2]
        embed.add_field(name=f'{guildname} guild', value=f'{guildmembers} Members\nGuild Leader: {leaderfirstname} {leaderlastname}\nColour code: #{guildcolor}{bankname}', inline=False)
        guildembeds += 1
        if guildembeds == 25:
            pagecount += 1
            embed.set_footer(text='Requested by {} | Page {}/? | RP Bot Ver {}'.format(ctx.author.display_name, pagecount, cfg['Version']))
            await ctx.send(embed=embed)
    if pagecount == 0:
        embed.set_footer(text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
    else:
        embed.set_footer(text='Requested by {} | Page {}/? | RP Bot Ver {}'.format(ctx.author.display_name, pagecount, cfg['Version']))
    await ctx.send(embed=embed)


@bot.command()
async def guildmembers(ctx, arg1=None):
    if arg1 is not None:
        cursor.execute('SELECT serverid FROM serversettings WHERE dcserverid=%s', (ctx.guild.id,))
        serverid = cursor.fetchone()[0]
        cursor.execute('SELECT guildid,guildcolor,guildname,guildleaderid FROM guilds WHERE serverid=%s AND guildname=%s', (serverid, arg1,))
        guilddata = cursor.fetchone()
        memberlist = ''
        if cursor.rowcount == 1:
            cursor.execute('SELECT userid,firstname,lastname FROM userinfo WHERE serverid=%s and guildid=%s', (serverid, guilddata[0],))
            memberdata = cursor.fetchall()
            embed = discord.Embed(title=f'{guilddata[2]} Guild Members', description=f'{guilddata[2]} Guild has {cursor.rowcount} members.', color=int(guilddata[1], 16))
            for row in memberdata:
                if row[0] == guilddata[3]:
                    memberlist += f' ♕ {row[1]} {row[2]}\n'
                else:
                    memberlist += f' --- {row[1]} {row[2]}\n'
            embed.add_field(name='Memberlist:', value=memberlist)
            embed.set_footer(text='Requested by {} | RP Bot Ver {}'.format(ctx.author.display_name, cfg['Version']))
            await ctx.send(embed=embed)
    else:
        await ctx.send('Please enter a guild name!\n`guildmembers <guildname>`')

# =============
# Economy stuff
# =============


#@bot.command()
#async def makeeconomy(ctx, arg1=None, arg2=None, dcuser: discord.User=None):
#    guildname = arg1
#    currencyname = arg2
#    bankermention = dcuser
#    if None not in (arg1, arg2, dcuser):


bot.run(cfg['Bottoken'])
