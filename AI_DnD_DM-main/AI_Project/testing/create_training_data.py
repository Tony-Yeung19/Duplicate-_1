import pandas as pd
import gzip
import json
import os
from collections import Counter
import re

def load_fireball_file(filepath):
    """Load all records from a single .jsonl.gz file"""
    data = []
    try:
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    data.append(record)
                except json.JSONDecodeError:
                    continue  #Skip malformed lines
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return data

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    #Remove extra whitespace, normalize quotes, etc.
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def expand_command(command):
    """Expand abbreviated commands for better training"""
    expansions = {
        '!a ': '!attack ',
        '!cast ': '!cast ',
        '!i ': '!initiative ',
        '!save ': '!save ',
        '!check ': '!check '
    }
    
    for short, full in expansions.items():
        if command.startswith(short):
            return command.replace(short, full, 1)
    return command

def create_dm_input_prompt(combat_state, before_utterances, utterance_history, current_actor):
    """Create structured input for DM training"""
    prompt = "As the Dungeon Master, respond to this game situation:\n\n"
    
    #Current combat state (limited to avoid overly long prompts)
    if combat_state and len(combat_state) > 0:
        prompt += "CURRENT COMBAT STATE:\n"
        for i, actor in enumerate(combat_state[:6]):  #Limit to 6 actors
            name = actor.get('name', 'Unknown')
            hp = actor.get('hp', '?')
            class_info = actor.get('class', '?')
            
            #Extract just the HP number if it's in format "XX/XX HP"
            hp_match = re.search(r'(\d+/\d+)', str(hp))
            hp_display = hp_match.group(1) if hp_match else str(hp)
            
            prompt += f"- {name}"
            if class_info and class_info != 'None':
                prompt += f" ({class_info})"
            prompt += f": HP {hp_display}"
            
            effects = actor.get('effects')
            if effects and effects != 'None':
                prompt += f" | Effects: {effects}"
            prompt += "\n"
    
    #Current actor context
    if current_actor and current_actor.get('name'):
        prompt += f"\nCURRENT TURN: {current_actor['name']}\n"
    
    #Player utterances/actions
    if before_utterances and len(before_utterances) > 0:
        clean_utterances = [clean_text(u) for u in before_utterances if clean_text(u)]
        if clean_utterances:
            prompt += f"\nPLAYER ACTION: {' '.join(clean_utterances)}\n"
    elif utterance_history and len(utterance_history) > 0:
        #Use recent chat history
        recent_chat = [clean_text(u) for u in utterance_history[-2:] if clean_text(u)]
        if recent_chat:
            prompt += "\nRECENT CHAT:\n"
            for msg in recent_chat:
                prompt += f"- {msg}\n"
    
    prompt += "\nDM RESPONSE:"
    return prompt

def create_dm_output(commands, automation_results, after_utterances):
    """Create training output for DM"""
    output_parts = []
    
    #System commands and results
    if commands and len(commands) > 0:
        expanded_commands = [expand_command(cmd) for cmd in commands]
        output_parts.append(f"COMMANDS: {' | '.join(expanded_commands)}")
    
    if automation_results and len(automation_results) > 0:
        clean_results = [clean_text(result) for result in automation_results]
        output_parts.append(f"RESULTS: {' | '.join(clean_results)}")
    
    #Narrative description (most important for training)
    if after_utterances and len(after_utterances) > 0:
        clean_narration = [clean_text(u) for u in after_utterances if clean_text(u)]
        if clean_narration:
            narration_text = ' '.join(clean_narration)
            output_parts.append(f"NARRATION: {narration_text}")
    
    return '\n'.join(output_parts) if output_parts else None

def calculate_quality_score(record):
    """Calculate quality score for training data filtering"""
    score = 0
    
    #Essential: Must have commands
    if record.get('commands_norm') and len(record['commands_norm']) > 0:
        score += 2
    else:
        return 0  #No commands = useless for training
    
    #Good: Has automation results
    if record.get('automation_results') and len(record['automation_results']) > 0:
        score += 1
    
    #Very good: Has before utterances (player intent)
    if record.get('before_utterances') and len(record['before_utterances']) > 0:
        score += 1
    
    #Excellent: Has after utterances (DM narration)
    if record.get('after_utterances') and len(record['after_utterances']) > 0:
        score += 2
    
    #Bonus: Has combat state
    if record.get('combat_state_before') and len(record['combat_state_before']) > 0:
        score += 1
    
    return score

def create_training_pairs_from_records(records, min_quality=3):
    """Create training pairs from a list of records"""
    training_pairs = []
    quality_distribution = Counter()
    
    for record in records:
        quality_score = calculate_quality_score(record)
        quality_distribution[quality_score] += 1
        
        if quality_score >= min_quality:
            input_text = create_dm_input_prompt(
                record.get('combat_state_before', []),
                record.get('before_utterances', []),
                record.get('utterance_history', []),
                record.get('current_actor', {})
            )
            
            output_text = create_dm_output(
                record.get('commands_norm', []),
                record.get('automation_results', []),
                record.get('after_utterances', [])
            )
            
            if input_text and output_text:
                training_pairs.append({
                    "input": input_text,
                    "output": output_text,
                    "quality_score": quality_score,
                    "has_narration": bool(record.get('after_utterances') and len(record['after_utterances']) > 0),
                    "has_player_action": bool(record.get('before_utterances') and len(record['before_utterances']) > 0)
                })
    
    return training_pairs, quality_distribution

def process_dataset_batch(data_dir, output_file, file_indices, batch_num):
    """Process a batch of files"""
    jsonl_files = [f for f in os.listdir(data_dir) if f.endswith('.jsonl.gz')]
    batch_files = [jsonl_files[i] for i in file_indices if i < len(jsonl_files)]
    
    all_records = []
    print(f"Batch {batch_num}: Processing {len(batch_files)} files...")
    
    for i, filename in enumerate(batch_files):
        filepath = os.path.join(data_dir, filename)
        records = load_fireball_file(filepath)
        all_records.extend(records)
        
        if (i + 1) % 50 == 0:
            print(f"  Loaded {i + 1}/{len(batch_files)} files...")
    
    print(f"  Creating training pairs from {len(all_records)} records...")
    training_pairs, quality_dist = create_training_pairs_from_records(all_records, min_quality=3)
    
    #Save this batch
    batch_output = f"batch_{batch_num}_{output_file}"
    with open(batch_output, 'w', encoding='utf-8') as f:
        for pair in training_pairs:
            f.write(json.dumps(pair) + '\n')
    
    print(f"  ✅ Saved {len(training_pairs)} pairs to {batch_output}")
    print(f"  Quality distribution: {dict(quality_dist)}")
    
    return len(training_pairs), quality_dist

def main():
    """Main processing pipeline"""
    data_dir = "C:/Users/Eliza/Downloads/Test Dataset AI/anonymized/filtered"
    output_file = "dm_training_data.jsonl"
    
    #Get all files
    jsonl_files = [f for f in os.listdir(data_dir) if f.endswith('.jsonl.gz')]
    print(f"Found {len(jsonl_files)} files in dataset")
    
    #Configuration
    TOTAL_FILES_TO_PROCESS = 1000  #Start with 1000 files
    BATCH_SIZE = 100  #Process 100 files at a time
    
    total_files = min(TOTAL_FILES_TO_PROCESS, len(jsonl_files))
    print(f"Processing {total_files} files in batches of {BATCH_SIZE}")
    
    all_training_pairs = []
    overall_quality_dist = Counter()
    
    #Process in batches
    for batch_start in range(0, total_files, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_files)
        batch_indices = range(batch_start, batch_end)
        batch_num = (batch_start // BATCH_SIZE) + 1
        
        batch_count, batch_quality = process_dataset_batch(
            data_dir, output_file, batch_indices, batch_num
        )
        
        #Merge quality distributions
        for score, count in batch_quality.items():
            overall_quality_dist[score] += count
        
        #Load and combine batches
        batch_filename = f"batch_{batch_num}_{output_file}"
        if os.path.exists(batch_filename):
            with open(batch_filename, 'r', encoding='utf-8') as f:
                batch_data = [json.loads(line) for line in f]
            all_training_pairs.extend(batch_data)
    
    #Save final combined dataset
    print(f"\nCreating final dataset with {len(all_training_pairs)} pairs...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for pair in all_training_pairs:
            f.write(json.dumps(pair) + '\n')
    
    #Final statistics
    print("\n" + "=" * 60)
    print("FINAL TRAINING DATASET STATISTICS")
    print("=" * 60)
    print(f"Total training pairs: {len(all_training_pairs):,}")
    print(f"Files processed: {total_files:,}")
    
    pairs_with_narration = sum(1 for p in all_training_pairs if p['has_narration'])
    pairs_with_player_action = sum(1 for p in all_training_pairs if p['has_player_action'])
    
    print(f"Pairs with DM narration: {pairs_with_narration} ({pairs_with_narration/len(all_training_pairs)*100:.1f}%)")
    print(f"Pairs with player actions: {pairs_with_player_action} ({pairs_with_player_action/len(all_training_pairs)*100:.1f}%)")
    print(f"Quality score distribution: {dict(overall_quality_dist)}")
    
    #Show some examples
    print("\n" + "=" * 60)
    print("TRAINING DATA EXAMPLES")
    print("=" * 60)
    
    for i, example in enumerate(all_training_pairs[:3]):
        print(f"\n--- Example {i+1} (Quality: {example['quality_score']}) ---")
        print("INPUT:")
        print(example['input'][:300] + "..." if len(example['input']) > 300 else example['input'])
        print("\nOUTPUT:")
        print(example['output'])
        print("-" * 50)

#------------------------------------------------------------------------------------------------

import json
import re
import random
from collections import Counter
import os

def clean_training_data(input_file, output_file):
    """Clean and validate the training data"""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        pairs = [json.loads(line) for line in f]
    
    print(f"Original pairs: {len(pairs)}")
    
    cleaned_pairs = []
    issues_found = {
        'duplicate_input': 0,
        'malformed_output': 0,
        'too_short': 0,
        'input_in_output': 0
    }
    
    seen_inputs = set()
    
    for pair in pairs:
        input_text = pair['input']
        output_text = pair['output']
        
        #Skip if input is a duplicate
        input_hash = hash(input_text[:200])  #Check first 200 chars for duplicates
        if input_hash in seen_inputs:
            issues_found['duplicate_input'] += 1
            continue
        seen_inputs.add(input_hash)
        
        #Skip if output is malformed (contains input content)
        if input_text in output_text:
            issues_found['input_in_output'] += 1
            continue
        
        #Skip if output is too short or just commands without narration
        if len(output_text.strip()) < 10:
            issues_found['too_short'] += 1
            continue
        
        #Clean the output - remove any malformed content
        output_clean = clean_output_text(output_text)
        
        if output_clean and len(output_clean) >= 10:
            cleaned_pair = {
                "input": input_text,
                "output": output_clean,
                "quality_score": pair['quality_score'],
                "has_narration": pair['has_narration'],
                "has_player_action": pair['has_player_action']
            }
            cleaned_pairs.append(cleaned_pair)
        else:
            issues_found['malformed_output'] += 1
    
    #Save cleaned data
    with open(output_file, 'w', encoding='utf-8') as f:
        for pair in cleaned_pairs:
            f.write(json.dumps(pair) + '\n')
    
    print(f"Cleaned pairs: {len(cleaned_pairs)}")
    print(f"Issues found: {issues_found}")
    print(f"Retention rate: {len(cleaned_pairs)/len(pairs)*100:.1f}%")
    
    return cleaned_pairs

def clean_output_text(output_text):
    """Clean malformed output text"""
    if not output_text:
        return None
    
    #Remove any input-like content that got copied
    lines = output_text.split('\n')
    clean_lines = []
    
    for line in lines:
        #Skip lines that look like they're from input
        if any(marker in line for marker in ['CURRENT COMBAT STATE', 'CURRENT TURN', 'PLAYER ACTION', 'RECENT CHAT', 'DM RESPONSE']):
            continue
        #Skip empty lines and malformed content
        if line.strip() and len(line.strip()) > 5:
            clean_lines.append(line.strip())
    
    return '\n'.join(clean_lines) if clean_lines else None

def create_synthetic_training_data(cleaned_real_data, num_examples=3000):
    """Create synthetic training examples to augment the dataset"""
    
    print(f"\nCreating {num_examples} synthetic examples...")
    
    #Analyze real data to create similar synthetic examples
    real_narrations = []
    real_commands = []
    
    for pair in cleaned_real_data:
        if 'NARRATION:' in pair['output']:
            narration_part = pair['output'].split('NARRATION:')[1].split('COMMANDS:')[0].strip()
            if narration_part:
                real_narrations.append(narration_part)
        
        if 'COMMANDS:' in pair['output']:
            command_part = pair['output'].split('COMMANDS:')[1].split('RESULTS:')[0].strip()
            if command_part:
                real_commands.extend([cmd.strip() for cmd in command_part.split('|')])
    
    #Character and monster templates based on your game data
    character_templates = [
        {"name": "Aelar", "class": "Wizard", "level": 5, "hp": "32/32", "spells": ["Fire Bolt", "Magic Missile", "Shield"]},
        {"name": "Borin", "class": "Fighter", "level": 5, "hp": "45/45", "weapons": ["Longsword", "Shortbow"]},
        {"name": "Celeste", "class": "Cleric", "level": 5, "hp": "38/38", "spells": ["Sacred Flame", "Healing Word", "Bless"]},
        {"name": "Darian", "class": "Rogue", "level": 5, "hp": "35/35", "weapons": ["Rapier", "Dagger", "Shortbow"]},
        {"name": "Eldrin", "class": "Ranger", "level": 5, "hp": "40/40", "weapons": ["Longbow", "Shortsword"]},
        {"name": "Fiona", "class": "Bard", "level": 5, "hp": "33/33", "spells": ["Vicious Mockery", "Healing Word", "Faerie Fire"]}
    ]
    
    monster_templates = [
        {"name": "Goblin", "hp": "7/7"},
        {"name": "Orc", "hp": "15/15"},
        {"name": "Wolf", "hp": "11/11"},
        {"name": "Skeleton", "hp": "13/13"},
        {"name": "Zombie", "hp": "22/22"},
        {"name": "Harpy", "hp": "38/38"},
        {"name": "Ogre", "hp": "59/59"},
        {"name": "Troll", "hp": "84/84"}
    ]
    
    #Player action templates
    action_templates = [
        "I attack the {monster} with my {weapon}!",
        "I cast {spell} at the {monster}!",
        "I use my {ability} on the {monster}!",
        "I swing my {weapon} at the nearest {monster}!",
        "I focus my magic and cast {spell}!",
        "I take aim with my {weapon} and fire at the {monster}!",
        "I channel divine energy and cast {spell}!",
        "I move into position and attack the {monster} with my {weapon}!"
    ]
    
    #DM narration templates
    narration_templates = [
        "The {weapon} strikes true, dealing a solid blow to the {monster}. It staggers back from the impact.",
        "{spell} erupts from {character}'s hands, engulfing the {monster} in magical energy. The creature howls in pain.",
        "With quick reflexes, {character} dodges the {monster}'s attack and counterattacks with their {weapon}.",
        "The {monster} lets out a roar as {character}'s attack finds its mark. The battle intensifies.",
        "{character} channels their inner power, {spell} taking effect on the battlefield with dazzling results.",
        "A well-aimed strike from {character}'s {weapon} causes the {monster} to stagger back, clearly wounded.",
        "The {monster} tries to evade, but {character}'s {spell} is too quick, striking it squarely.",
        "{character} moves with precision, their {weapon} slicing through the air towards the {monster}."
    ]
    
    #Command templates based on real data patterns
    command_templates = [
        "!attack {weapon} -t {monster}",
        "!cast {spell} -t {monster}",
        "!a {weapon} -t {monster}",
        "!cast {spell}"
    ]
    
    synthetic_pairs = []
    
    for i in range(num_examples):
        char = random.choice(character_templates)
        monster = random.choice(monster_templates)
        
        #Determine action type (attack or spell)
        use_spell = random.random() < 0.4  #40% chance to use spell
        
        if use_spell and 'spells' in char:
            spell = random.choice(char['spells'])
            weapon = "staff"  #Default for spellcasters
            action_template = random.choice([t for t in action_templates if '{spell}' in t])
            player_action = action_template.format(spell=spell, monster=monster['name'])
            
            narration_template = random.choice([t for t in narration_templates if '{spell}' in t])
            narration = narration_template.format(
                spell=spell, 
                character=char['name'], 
                monster=monster['name'],
                weapon=weapon
            )
            
            command = random.choice([t for t in command_templates if '{spell}' in t])
            command = command.format(spell=spell, monster=monster['name'])
            
        else:
            weapon = random.choice(char.get('weapons', ['longsword', 'axe', 'mace', 'spear']))
            action_template = random.choice([t for t in action_templates if '{weapon}' in t])
            player_action = action_template.format(weapon=weapon, monster=monster['name'])
            
            narration_template = random.choice([t for t in narration_templates if '{weapon}' in t])
            narration = narration_template.format(
                weapon=weapon, 
                character=char['name'], 
                monster=monster['name'],
                spell="magic"  #Fallback
            )
            
            command = random.choice([t for t in command_templates if '{weapon}' in t])
            command = command.format(weapon=weapon, monster=monster['name'])
        
        #Create combat state (1-3 characters)
        num_chars = random.randint(1, 3)
        combat_chars = [char] + random.sample(character_templates, num_chars-1)
        
        #Build input
        input_text = f"""As the Dungeon Master, respond to this game situation:

CURRENT COMBAT STATE:"""
        
        for combat_char in combat_chars:
            effects = random.choice(['', ' | Effects: Blessed', ' | Effects: Hasted', ' | Effects: Inspired'])
            input_text += f"\n- {combat_char['name']} ({combat_char['class']}): HP {combat_char['hp']}{effects}"
        
        input_text += f"\n- {monster['name']}: HP {monster['hp']}"

        input_text += f"\n\nCURRENT TURN: {char['name']}"
        input_text += f"\n\nPLAYER ACTION: {player_action}"
        input_text += f"\n\nDM RESPONSE:"
        
        #Build output
        result_text = f"{char['name']} uses {spell if use_spell else weapon}!"
        output_text = f"COMMANDS: {command}\nRESULTS: {result_text}\nNARRATION: {narration}"
        
        synthetic_pairs.append({
            "input": input_text,
            "output": output_text,
            "quality_score": 7,  #High quality synthetic data
            "has_narration": True,
            "has_player_action": True,
            "synthetic": True
        })
        
        if (i + 1) % 500 == 0:
            print(f"  Created {i + 1} synthetic examples...")
    
    print(f"Created {len(synthetic_pairs)} synthetic training examples")
    return synthetic_pairs

def create_final_training_dataset(cleaned_real_data, synthetic_data, output_dir="."):
    """Combine cleaned real data with synthetic data and create train/val splits"""
    
    print(f"\nCreating final dataset...")
    print(f"Real data: {len(cleaned_real_data)} examples")
    print(f"Synthetic data: {len(synthetic_data)} examples")
    
    #Combine datasets
    final_data = cleaned_real_data + synthetic_data
    
    #Shuffle the data
    random.shuffle(final_data)
    
    #Split into train/validation (90/10 split)
    split_idx = int(0.9 * len(final_data))
    train_data = final_data[:split_idx]
    val_data = final_data[split_idx:]
    
    #Save splits
    train_file = os.path.join(output_dir, "train_dataset.jsonl")
    val_file = os.path.join(output_dir, "val_dataset.jsonl")
    
    with open(train_file, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item) + '\n')
    
    with open(val_file, 'w', encoding='utf-8') as f:
        for item in val_data:
            f.write(json.dumps(item) + '\n')
    
    #Statistics
    real_in_train = sum(1 for item in train_data if not item.get('synthetic', False))
    real_in_val = sum(1 for item in val_data if not item.get('synthetic', False))
    synthetic_in_train = sum(1 for item in train_data if item.get('synthetic', False))
    synthetic_in_val = sum(1 for item in val_data if item.get('synthetic', False))
    
    print(f"\nFINAL DATASET COMPOSITION:")
    print(f"Training examples: {len(train_data)}")
    print(f"  - Real data: {real_in_train}")
    print(f"  - Synthetic data: {synthetic_in_train}")
    print(f"Validation examples: {len(val_data)}")
    print(f"  - Real data: {real_in_val}")
    print(f"  - Synthetic data: {synthetic_in_val}")
    print(f"Total examples: {len(final_data)}")
    
    #Quality statistics
    train_with_narration = sum(1 for item in train_data if item['has_narration'])
    val_with_narration = sum(1 for item in val_data if item['has_narration'])
    
    print(f"\nQUALITY METRICS:")
    print(f"Training set narration rate: {train_with_narration}/{len(train_data)} ({train_with_narration/len(train_data)*100:.1f}%)")
    print(f"Validation set narration rate: {val_with_narration}/{len(val_data)} ({val_with_narration/len(val_data)*100:.1f}%)")
    
    return train_data, val_data

def main():
    """Main function to create enhanced training dataset"""
    
    input_file = "dm_training_data.jsonl"
    cleaned_file = "dm_training_data_cleaned.jsonl"
    
    print("=" * 70)
    print("ENHANCED TRAINING DATASET CREATION")
    print("=" * 70)
    
    #Step 1: Clean the original data
    print("\nSTEP 1: Cleaning original data")
    cleaned_real_data = clean_training_data(input_file, cleaned_file)
    
    #Step 2: Create synthetic data to boost narration quality
    print("\nSTEP 2: Creating synthetic data")
    synthetic_data = create_synthetic_training_data(cleaned_real_data, num_examples=3000)
    
    #Step 3: Combine and create final dataset
    print("\nSTEP 3: Creating final dataset splits")
    train_data, val_data = create_final_training_dataset(cleaned_real_data, synthetic_data)
    
    print("\n" + "=" * 70)
    print("ENHANCED TRAINING DATASET CREATION COMPLETE!")
    print("=" * 70)
    print("\nGenerated files:")
    print(f"  - {cleaned_file} (Cleaned real data)")
    print(f"  - train_dataset.jsonl (Training set)")
    print(f"  - val_dataset.jsonl (Validation set)")
    
    #Show some final examples
    print("\n" + "=" * 70)
    print("FINAL DATASET EXAMPLES")
    print("=" * 70)
    
    #Show one real and one synthetic example
    real_examples = [item for item in train_data if not item.get('synthetic', False)][:1]
    synthetic_examples = [item for item in train_data if item.get('synthetic', False)][:1]
    
    if real_examples:
        print(f"\n--- REAL EXAMPLE (Quality: {real_examples[0]['quality_score']}) ---")
        print("INPUT:")
        print(real_examples[0]['input'][:400] + "..." if len(real_examples[0]['input']) > 400 else real_examples[0]['input'])
        print("\nOUTPUT:")
        print(real_examples[0]['output'])
    
    if synthetic_examples:
        print(f"\n--- SYNTHETIC EXAMPLE ---")
        print("INPUT:")
        print(synthetic_examples[0]['input'][:400] + "..." if len(synthetic_examples[0]['input']) > 400 else synthetic_examples[0]['input'])
        print("\nOUTPUT:")
        print(synthetic_examples[0]['output'])

if __name__ == "__main__":

    main()
