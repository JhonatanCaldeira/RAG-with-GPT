import discord
from dotenv import load_dotenv
import os
from components.gpt import openai_request, openai_vision
from components.brave_api import brave_request
from components.tools import download_pdf_file, get_pdf_text
import re

load_dotenv(dotenv_path='components/.env')
token = os.environ['BOT_TOKEN']

msg_system = """
Vous êtes le maître suprême des tables de jeu de rôle, votre but est : 
1- Aider les joueurs avec des règles et des conseils des systèmes les plus variés. 
3- Vous répondrez toujours dans la même langue! Si on te demande en Frances, 
tu répondras en Frances, par exemple.
"""

casual_msg_system = """
Tu es TheRealMaster.
Tu es là pour interagir et badinet avec les utilisateurs du discord.
Limite tes réponses à 2000 caractères maximum.
"""

msg_summarization = """
Vous êtes une IA hautement qualifiée formée à la compréhension et à la synthèse des langues. 
J’aimerais que vous lisiez le texte suivant et que vous le résumiez 
Objectif de conserver les points les plus importants, en fournissant un 
Résumé cohérent et lisible qui pourrait aider une personne à comprendre le principal 
les points de discussion sans avoir à lire le texte en entier. 
Veuillez éviter les détails inutiles ou les points tangentiels.
Vous devez générer le paragraphe abstrait dans la même langue que le texte original.
"""

oracle_msg_system = """
Tu vas classifier les questions que l'ont te pose en deux categories:
- Recherche d'informations:
L'utilisateur te pose une question très précise et/ou technique qui nécessite
des informations en plus de tes connaissances actuelles.
- Discussions et instructions:
L'utilisateur cherche seulement à converser avec toi et te demande de générer
des textes ou autres.
Tu ne peux répondre que par '0' ou '1'. rien d'autres.
Si la catégorie est Recherche d'informations,
alors tu réponds 0 sinon tu réponds 1.
"""

oracle_conv = [{"role": "system", "content": oracle_msg_system}]


# connect to discord
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# log
@client.event
async def on_ready():
    print("Logged as {0.user}".format(client))

# answerer
@client.event
async def on_message(message):

    if message.author == client.user:
        return

    if (message.channel.name in ["bot"] 
        and client.user.mentioned_in(message)
        and message.mention_everyone is False):

        async with message.channel.typing():

            msg = str(message.content)

            if message.attachments:
                #Checking the Images
                if "image" in message.attachments[0].content_type:
                    content = [{"type":"text", 
                                "text": re.sub("<@\d+>", "", msg),}]

                    for attch in message.attachments:
                        content.append({"type": "image_url",
                                        "image_url": {"url":attch.url},})
                        
                    vision_input = [{"role": "user", "content": content}]
                    reply = openai_vision(vision_input)      

                #Checking the PDF
                elif "pdf" in message.attachments[0].content_type:
                    response, filepath = download_pdf_file(message.attachments[0].url)
                    if response:
                        pdf_text = get_pdf_text(filepath)

                        summarization = [{"role":"system", 
                                          "content": msg_summarization}]
                        
                        summarization.append({"role":"user", "content": pdf_text})
                        reply = openai_request(summarization)
                
            else: 
                msg = message.content
                oracle_prompt = oracle_conv.copy()
                oracle_prompt.append({"role": "user", "content": msg})
                response_oracle = openai_request(oracle_prompt)

                # With RAG
                if response_oracle == "0":        
                    current_conv = [{"role":"system", "content": msg_system}]
                    current_conv.append({"role":"user", "content": msg})

                    brave_output = brave_request(msg)
                    current_conv.append({"role":"system","content": 
                                        str(brave_output["results"][:5])})
                
                    reply = openai_request(current_conv)
                
                #Whitout RAG
                else:
                    current_conv = [{"role":"system", "content": casual_msg_system}]
                    current_conv.append({"role":"user", "content": msg})
                    reply = openai_request(current_conv)

                
            await message.reply(reply, mention_author=True)

client.run(token)