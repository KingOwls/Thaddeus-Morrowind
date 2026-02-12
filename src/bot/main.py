import os
import sys
import signal
import logging
import traceback

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Opcional: para que slash aparezca al instante en tu servidor de pruebas
GUILD_ID = os.getenv("GUILD_ID")  # ponlo en .env si quieres

EXTENSIONS = [
    "src.bot.cogs.ping",
    "src.bot.cogs.personaje",
]


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def explain_exception(e: Exception) -> str:
    """Convierte excepciones comunes en mensajes claros para consola."""
    msg = str(e)

    # Casos típicos
    if isinstance(e, commands.ExtensionNotFound):
        return (
            "❌ EXTENSION NO ENCONTRADA\n"
            f"   Detalle: {msg}\n"
            "   Causa común: el archivo no existe o falta __init__.py.\n"
            "   Revisa: src/bot/cogs/<archivo>.py y __init__.py en src/, bot/, cogs/."
        )

    if isinstance(e, commands.ExtensionFailed):
        return (
            "❌ EXTENSION FALLÓ AL CARGAR\n"
            f"   Detalle: {msg}\n"
            "   Causa común: error dentro del cog (import, sintaxis, etc).\n"
            "   Mira el traceback arriba para la línea exacta."
        )

    if isinstance(e, discord.Forbidden):
        return (
            "❌ PERMISOS INSUFICIENTES (Forbidden)\n"
            f"   Detalle: {msg}\n"
            "   Causa común: el bot no tiene permisos en ese canal/servidor."
        )

    if isinstance(e, discord.HTTPException):
        return (
            "❌ ERROR HTTP DE DISCORD\n"
            f"   Detalle: {msg}\n"
            "   Puede ser rate-limit, payload inválido o error temporal."
        )

    return f"❌ ERROR: {msg}"


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Necesario para comandos con prefijo (=)
        super().__init__(command_prefix="=", intents=intents)

    async def setup_hook(self):
        logging.info("🚀 Iniciando setup_hook: cargando extensiones...")

        # 1) Cargar extensiones
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                logging.info("✅ Loaded extension: %s", ext)
            except Exception as e:
                logging.error(explain_exception(e))
                logging.debug("TRACEBACK:\n%s", traceback.format_exc())

        # 2) Sincronizar slash commands (guild para test, global para prod)
        try:
            if GUILD_ID:
                guild = discord.Object(id=int(GUILD_ID))
                synced = await self.tree.sync(guild=guild)
                logging.info("⚡ Synced %d slash commands (GUILD %s).", len(synced), GUILD_ID)
            else:
                synced = await self.tree.sync()
                logging.info("🌍 Synced %d slash commands (GLOBAL).", len(synced))

            # Lista de comandos sincronizados
            for cmd in synced:
                logging.info("   /%s", cmd.name)

        except Exception as e:
            logging.error("❌ Failed to sync slash commands.")
            logging.error(explain_exception(e))
            logging.debug("TRACEBACK:\n%s", traceback.format_exc())

    async def on_ready(self):
        logging.info("🟢 BOT ACTIVO: %s (ID: %s)", self.user, self.user.id)
        logging.info("📌 Prefix: usa =ping")
        logging.info("📌 Slash: usa /ping y /pj ...")
        logging.info("🧯 Para apagar: Ctrl + C en la consola (apagado limpio).")

    async def on_connect(self):
        logging.info("🔌 Conectando a Discord Gateway...")

    async def on_disconnect(self):
        logging.warning("🔌 Desconectado del Gateway. Discord intentará reconectar...")

    async def on_resumed(self):
        logging.info("🔁 Conexión reanudada (resume).")

    # =========
    # Errores de comandos prefijo (=)
    # =========
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            logging.warning("⚠️ Comando no encontrado: %s", ctx.message.content)
            return

        logging.error("❌ Error en comando prefijo: %s", ctx.message.content)
        logging.error(explain_exception(error))
        logging.debug("TRACEBACK:\n%s", traceback.format_exc())

    # =========
    # Errores de slash commands (/)
    # =========
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        name = getattr(interaction.command, "name", "unknown")
        logging.error("❌ Error en slash /%s", name)
        logging.error(explain_exception(error))
        logging.debug("TRACEBACK:\n%s", traceback.format_exc())

        # Mensaje al usuario (ephemeral) con algo legible
        try:
            if interaction.response.is_done():
                await interaction.followup.send("Ocurrió un error ejecutando el comando. El staff ya fue notificado.", ephemeral=True)
            else:
                await interaction.response.send_message("Ocurrió un error ejecutando el comando. El staff ya fue notificado.", ephemeral=True)
        except Exception:
            pass


def main():
    setup_logging()

    logging.info("==============================")
    logging.info("🧪 Iniciando bot...")
    logging.info("LOG_LEVEL=%s", LOG_LEVEL)
    if GUILD_ID:
        logging.info("GUILD_ID=%s (sync rápido activado)", GUILD_ID)
    logging.info("==============================")

    if not TOKEN:
        raise RuntimeError("Falta DISCORD_TOKEN en tu .env")

    bot = MyBot()

    # Apagado bonito con Ctrl+C
    def handle_shutdown(sig, frame):
        logging.warning("🛑 Señal de apagado recibida (Ctrl+C). Cerrando bot...")
        try:
            # close() es async, pero podemos salir con sys.exit después de run
            # bot.run maneja cierre al recibir KeyboardInterrupt
            pass
        finally:
            # Fuerza salida del proceso si algo queda colgado
            sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)

    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logging.warning("🛑 Bot detenido por KeyboardInterrupt (Ctrl+C).")
    except Exception as e:
        logging.error("❌ Error fatal arrancando el bot.")
        logging.error(explain_exception(e))
        logging.debug("TRACEBACK:\n%s", traceback.format_exc())
    finally:
        logging.info("✅ Proceso finalizado.")


if __name__ == "__main__":
    main()
