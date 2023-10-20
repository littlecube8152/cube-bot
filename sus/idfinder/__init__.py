import discord
from discord.ext import commands
import subprocess
import re


class StudentIDFinder:
    class InvalidIDError(Exception):
        pass

    @classmethod
    def raw_query_id(cls, student_id):
        """
        Query `student_id` using ldap.  
        Raise InvalidIDError if student_id is not a valid id.
        Return None if the given `student_id` has no entry for name.
        """
        if not re.match(r"^[br][0-9]{8}$", student_id):
            raise cls.InvalidIDError
        
        res = subprocess.run(["getName", student_id], capture_output=True)

        if res.returncode != 0: # catch base64 error
            return None
        if res.stdout == b"\n": # catch no entry
            return None
        
        return res.stdout.decode()
    
    def query_id(cls, student_id):
        """
        Same as `raw_query_id` but does not raise exception.
        """
        try:
            name = cls.raw_query_id(student_id)
        except cls.InvalidIDError:
            return None
        return name

class StudentIDCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command()
    async def get_name(self, ctx, student_id: str = ""):
        """
        Get a given name of id by ldap on workstation.
        """
        try:
            res = StudentIDFinder.raw_query_id(student_id)
        except StudentIDFinder.InvalidIDError:
            await ctx.respond(f"Error! ID is not valid.")
            return
        
        name = "Not found" if res == None else f"`{res}`"
        await ctx.respond(f"`{student_id}` → {name}")
