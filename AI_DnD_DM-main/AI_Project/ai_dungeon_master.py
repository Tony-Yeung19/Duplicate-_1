import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import json
import re

class AIDungeonMaster:
    def __init__(self, model_path):
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        self.load_model()
        
    def load_model(self):
        """Load your trained AI model"""
        print("Loading AI Dungeon Master...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_path)
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        print("AI Dungeon Master loaded!")
    
    def create_game_state_prompt(self, game_state, player_action):
        """Create prompt that guides the AI to generate better responses"""
        prompt = f"""You are an expert Dungeon Master running a D&D 5e game. Respond to the player's action following these guidelines:

GUIDELINES:
- Generate exactly ONE game command if the action requires mechanical resolution
- If the player casts a spell, generate a !cast command with the spell name
- Healing spells should target wounded allies, damage spells target enemies
- Write 1-2 sentences of descriptive narration that matches the game mechanics
- Keep narration clear, coherent, and focused on what actually happens
- Avoid markdown formatting, asterisks for actions, or random dialogue
- Never include multiple attacks or turns in one response
- If the action fails, describe why it failed realistically

CURRENT GAME STATE:
        {self.format_game_state(game_state)}

PLAYER ACTION: {player_action}

Generate your response in this exact format:

COMMANDS: [command if needed, otherwise leave blank]
NARRATION: [1-2 sentence description of what happens]

DM RESPONSE:"""
        return prompt
    
    def format_game_state(self, game_state):
        """Format game state for AI prompts - same as in AIDungeonMaster - FIXED"""
        state_text = ""
        
        #Characters section
        if 'characters' in game_state and game_state['characters']:
            state_text += "CHARACTERS:\n"
            for char in game_state['characters']:
                state_text += f"- {char['name']} ({char.get('class', 'Adventurer')} Lvl {char.get('level', 1)}): "
                state_text += f"HP {char.get('hit_points', '?')}/{char.get('max_hit_points', '?')} | "
                state_text += f"AC {char.get('armor_class', '?')}"
                
                #Add stats if available
                if 'stats' in char:
                    stats = char['stats']
                    state_text += f" | STR:{stats.get('strength', '?')} DEX:{stats.get('dexterity', '?')} CON:{stats.get('constitution', '?')}"
                
                state_text += "\n"
        
        #Monsters section  
        if 'monsters' in game_state and game_state['monsters']:
            state_text += "MONSTERS:\n"
            for monster in game_state['monsters']:
                state_text += f"- {monster['name']}: "
                state_text += f"HP {monster.get('current_hp', monster.get('hit_points', '?'))}/{monster.get('hit_points', '?')} | "
                state_text += f"AC {monster.get('armor_class', '?')}"
                
                #Add monster type - FIXED: Use special_abilities instead of abilities
                if 'type' in monster:
                    state_text += f" | {monster['type']}"
                
                #Add special abilities if available (not ability scores)
                if 'special_abilities' in monster and monster['special_abilities']:
                    #Take first 3 special ability names
                    ability_names = [ability['name'] for ability in monster['special_abilities'][:3]]
                    state_text += f" | Abilities: {', '.join(ability_names)}"
                
                state_text += "\n"
        
        #Combat state
        if game_state.get('combat_active', False):
            state_text += f"COMBAT: Round {game_state.get('round', 1)} | "
            state_text += f"Current Turn: {game_state.get('current_turn', 'Unknown')}\n"
        else:
            state_text += "MODE: Exploration\n"
        
        #Environment
        if 'environment' in game_state:
            state_text += f"LOCATION: {game_state['environment']}\n"
            
        return state_text
    
    def generate_response(self, game_state, player_action, max_length=200):
        """Generate AI DM response with proper error handling - FIXED REPETITION"""
        try:
            print(f"DEBUG: Generating response for action: {player_action}")
            prompt = self.create_game_state_prompt(game_state, player_action)
            print(f"DEBUG: Prompt created successfully")
            
            inputs = self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
            print(f"DEBUG: Inputs tokenized successfully")
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=0.8,  #Increased for more variety
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.5,  #Increased to reduce repetition
                    top_p=0.92,  #Adjusted for better sampling
                    top_k=50,    #Added to limit vocabulary choices
                    no_repeat_ngram_size=3  #Prevent repeating 3-grams
                )
            print(f"DEBUG: Model generation completed")
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            print(f"DEBUG: Raw model response: {response}")
            
            #Extract just the response part
            if "DM RESPONSE:" in response:
                response = response.split("DM RESPONSE:")[1].strip()
            elif "Response:" in response:
                response = response.split("Response:")[1].strip()
            
            return self.parse_dm_response(response)
            
        except Exception as e:
            print(f"DEBUG: Error in generate_response: {e}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            #Return a fallback response
            return {
                'commands': [],
                'narration': f"The DM is considering your action: '{player_action}'",
                'raw_response': f"Error: {e}"
            }
    
    def parse_dm_response(self, response):
        """Parse AI response according to your training data format"""

        self.debug_command_parsing(response)

        commands = []
        narration = ""
        
        #ULTRA ROBUST COMMAND PARSING
        #Method 1: Look for COMMANDS: section with regex
        commands_pattern = r'COMMANDS:\s*(.*?)(?:\n\s*[A-Z]|RESULTS:|NARRATION:|$)' 
        commands_match = re.search(commands_pattern, response, re.IGNORECASE | re.DOTALL)
        
        if commands_match:
            command_text = commands_match.group(1).strip()
            print(f"DEBUG: Found command text: '{command_text}'")
            
            #Extract individual commands
            if command_text:
                #Split by various separators
                separators = [';', '\n', ',', ' and ']
                for sep in separators:
                    if sep in command_text:
                        raw_commands = command_text.split(sep)
                        break
                else:
                    raw_commands = [command_text]
                
                for cmd in raw_commands:
                    clean_cmd = cmd.strip()
                    if clean_cmd and clean_cmd.startswith('!'):
                        commands.append(clean_cmd)
                        print(f"DEBUG: Added command: {clean_cmd}")
        
        #Method 2: Direct pattern matching in entire response
        if not commands:
            print("DEBUG: Trying direct pattern matching")
            #Look for !attack patterns anywhere in response
            attack_patterns = [
                r'!attack\s+\w+\s+-t\s+\w+',
                r'!attack\s+\w+.*?-t\s+\w+',
                r'!a\s+\w+\s+-t\s+\w+'
            ]
            
            for pattern in attack_patterns:
                found_commands = re.findall(pattern, response, re.IGNORECASE)
                commands.extend(found_commands)
                if found_commands:
                    print(f"DEBUG: Found commands via pattern {pattern}: {found_commands}")
        
        #Method 3: Extract from natural language
        if not commands:
            print("DEBUG: Trying natural language extraction")
            natural_commands = self.extract_commands_from_natural_language(response)
            commands.extend(natural_commands)
            if natural_commands:
                print(f"DEBUG: Found natural language commands: {natural_commands}")
        
        #Spell command detection:
        spell_commands = re.findall(r'!cast\s+\w+(?:\s+\w+)*\s*(?:-t\s+\w+)?', response, re.IGNORECASE)
        commands.extend(spell_commands)
        if spell_commands:
            print(f"DEBUG: Found spell commands: {spell_commands}")

        clean_response = self.clean_response_text(response)

        #Remove duplicates
        commands = list(dict.fromkeys(commands))
        
        narration = "The action unfolds."

        #EXTRACT NARRATION
        if "NARRATION:" in response:
            narration_section = response.split("NARRATION:")[1]
            
            #Find the end of narration section
            end_markers = ["COMMANDS:", "RESULTS:", "DM RESPONSE:", "\n\n", "Narrations:"]
            for marker in end_markers:
                if marker in narration_section:
                    narration_section = narration_section.split(marker)[0]
            
            raw_narration = narration_section.strip()
            
            #Clean the narration aggressively
            narration = self.clean_chaotic_narration(raw_narration)
            
        else:
            #Fallback: look for the first coherent paragraph
            paragraphs = response.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if (len(para) > 20 and 
                    len(para) < 200 and
                    not para.startswith('COMMANDS:') and
                    not para.startswith('RESULTS:') and
                    not any(word in para.lower() for word in ['narrat', 'dm ', 'response'])):
                    narration = self.clean_chaotic_narration(para)
                    break
        
        #Clean up narration
        narration = self.clean_chaotic_narration(narration)
        commands, narration = self.validate_and_improve_response(commands, narration)
        
        print(f"DEBUG: Final - Commands: {commands}, Narration: {narration}")
        
        return {
            'commands': commands,
            'narration': narration,
            'raw_response': response
        }

    def clean_chaotic_narration(self, text):
        """Clean up chaotic AI narration - MORE AGGRESSIVE"""
        if not text or text == "The action unfolds.":
            return "The action unfolds."
        
        import re
        
        #Remove ALL markdown and formatting
        text = re.sub(r'\*.*?\*', '', text)  #Remove *italic* text
        text = re.sub(r'\*{2}.*?\*{2}', '', text)  #Remove **bold** text
        text = re.sub(r'_.*?_', '', text)  #Remove _italic_ text
        text = re.sub(r'`.*?`', '', text)  #Remove `code` text
        
        #Remove random ALL CAPS words and garbage
        text = re.sub(r'\b[A-Z]{4,}\b', '', text)
        text = re.sub(r'[A-Z]{3,}', '', text)
        
        #Remove incomplete sentences and fragments
        text = re.sub(r'[^.!?]*\*[^.!?]*[.!?]', '', text)  #Remove lines with *
        text = re.sub(r'^.*?narrations?:?', '', text, flags=re.IGNORECASE)  #Remove "narrations:" prefixes
        
        #Extract only complete sentences
        sentences = re.findall(r'[^.!?]*[.!?]', text)
        clean_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            #Filter criteria for good sentences
            if (len(sentence) > 10 and 
                len(sentence) < 150 and
                not any(word in sentence.lower() for word in ['narrat', 'results', 'commands', 'dm respon']) and
                not sentence.startswith('*') and
                not sentence.endswith('*') and
                '"' not in sentence or sentence.count('"') >= 2):  #Either no quotes or balanced quotes
                clean_sentences.append(sentence)
        
        #Take only first 2 good sentences
        if clean_sentences:
            text = ' '.join(clean_sentences[:2])
        else:
            #Fallback: try to extract any reasonable text
            words = text.split()
            if len(words) > 5:
                text = ' '.join(words[:15]) + '...'
            else:
                text = "The action unfolds."
        
        #Final cleanup
        text = re.sub(r'\s+', ' ', text).strip()
        text = text[0].upper() + text[1:] if text else "The action unfolds."
        
        return text

    def clean_response_text(self, response):
        """Clean up the AI response text - IMPROVED"""
        #Remove the prompt part if it's included
        if "DM RESPONSE:" in response:
            response = response.split("DM RESPONSE:")[1].strip()
        elif "Response:" in response:
            response = response.split("Response:")[1].strip()
        
        #Remove everything after obvious garbage markers
        garbage_markers = ["DM RESPON", "NOMENT CHAT", "RESULTSruction", "NarrATION:", "NURRATION:"]
        for marker in garbage_markers:
            if marker in response:
                response = response.split(marker)[0].strip()
        
        #Remove lines that are clearly not narration
        lines = response.split('\n')
        clean_lines = []
        for line in lines:
            line = line.strip()
            #Skip lines that are section headers or garbage
            if (line and 
                not line.startswith('COMMANDS:') and 
                not line.startswith('RESULTS:') and
                not line.startswith('NARRATION:') and
                not line.startswith('DM ') and
                not line.startswith('NOMENT') and
                not line.startswith('RESULTSruction') and
                len(line) > 5):  #Skip very short lines
                clean_lines.append(line)
        
        return ' '.join(clean_lines)
    
    def validate_and_improve_response(self, commands, narration):
        """Validate and improve the AI response quality"""
        #If narration is garbage but we have commands, create better narration
        if (commands and 
            (narration == "The action unfolds." or 
            len(narration) < 10 or
            any(word in narration.lower() for word in ['narrat', 'results', 'commands']))):
            
            #Create context-appropriate narration
            if commands[0].startswith('!attack'):
                parts = commands[0].split()
                if len(parts) >= 4 and '-t' in parts:
                    target_index = parts.index('-t') + 1
                    if target_index < len(parts):
                        target = parts[target_index]
                        weapon = parts[1] if len(parts) > 1 else "weapon"
                        narration = f"The {weapon} attack against the {target} connects!"
        
        #Ensure narration starts with capital letter and ends with punctuation
        if narration and narration != "The action unfolds.":
            narration = narration[0].upper() + narration[1:]
            if not narration.endswith(('.', '!', '?')):
                narration += '.'
        
        return commands, narration

    def extract_commands_from_natural_language(self, text):
        """Fallback: extract commands from natural language"""
        commands = []
        text_lower = text.lower()
        
        #Look for attack patterns
        if any(word in text_lower for word in ['attack', 'hit', 'strike', 'swing']):
            #Extract target
            target = None
            for monster in ['wolf', 'goblin', 'orc', 'zombie', 'skeleton']:
                if monster in text_lower:
                    target = monster.capitalize()
                    break
            
            #Extract weapon
            weapon = None
            weapon_map = {
                'crossbow': 'Light Crossbow',
                'sword': 'Longsword', 
                'rapier': 'Rapier',
                'dagger': 'Dagger',
                'mace': 'Mace',
                'axe': 'Greataxe',
                'bow': 'Shortbow'
            }
            
            for weapon_word, weapon_name in weapon_map.items():
                if weapon_word in text_lower:
                    weapon = weapon_name
                    break
            
            if target and weapon:
                commands.append(f"!attack {weapon} -t {target}")
        
        return commands
    
    def debug_command_parsing(self, response):
        """Temporary debug method to see command parsing steps"""
        print("=== COMMAND PARSING DEBUG ===")
        print(f"Original: {response}")
        
        #Test COMMANDS: pattern
        commands_pattern = r'COMMANDS:\s*(.*?)(?:\n\s*[A-Z]|RESULTS:|NARRATION:|$)'
        commands_match = re.search(commands_pattern, response, re.IGNORECASE | re.DOTALL)
        print(f"COMMANDS pattern match: {commands_match}")
        if commands_match:
            print(f"COMMANDS group: '{commands_match.group(1)}'")
        
        #Test direct pattern
        direct_pattern = r'!attack\s+\w+\s+-t\s+\w+'
        direct_match = re.findall(direct_pattern, response, re.IGNORECASE)
        print(f"Direct pattern match: {direct_match}")
        
        print("=== END DEBUG ===")