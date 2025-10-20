import json
from collections import Counter

def analyze_training_file(filename):
    """Analyze the created training dataset"""
    with open(filename, 'r', encoding='utf-8') as f:
        pairs = [json.loads(line) for line in f]
    
    print(f"Analyzing {len(pairs)} training pairs from {filename}")
    
    #Basic stats
    quality_scores = [p['quality_score'] for p in pairs]
    has_narration = sum(1 for p in pairs if p['has_narration'])
    has_player_action = sum(1 for p in pairs if p['has_player_action'])
    
    print(f"Quality scores: {Counter(quality_scores)}")
    print(f"With narration: {has_narration} ({has_narration/len(pairs)*100:.1f}%)")
    print(f"With player actions: {has_player_action} ({has_player_action/len(pairs)*100:.1f}%)")
    
    #Analyze input/output lengths
    input_lens = [len(p['input']) for p in pairs]
    output_lens = [len(p['output']) for p in pairs]
    
    print(f"Average input length: {sum(input_lens)/len(input_lens):.0f} chars")
    print(f"Average output length: {sum(output_lens)/len(output_lens):.0f} chars")
    print(f"Max input length: {max(input_lens)} chars")
    print(f"Max output length: {max(output_lens)} chars")
    
    #Show command patterns
    all_outputs = [p['output'] for p in pairs]
    commands_used = []
    for output in all_outputs:
        if 'COMMANDS:' in output:
            cmd_part = output.split('COMMANDS:')[1].split('RESULTS:')[0].strip()
            commands_used.extend([cmd.strip() for cmd in cmd_part.split('|')])
    
    print(f"\nMost common commands:")
    cmd_counter = Counter(commands_used)
    for cmd, count in cmd_counter.most_common(10):
        print(f"  {cmd}: {count}")

#Run analysis after creating training data

analyze_training_file("dm_training_data.jsonl")
