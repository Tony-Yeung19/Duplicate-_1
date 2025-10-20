import pandas as pd
import gzip
import json
from collections import Counter
import os

def load_complete_fireball_file(filepath):
    """Load ALL records from a .jsonl.gz file"""
    data = []
    try:
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                try:
                    record = json.loads(line.strip())
                    data.append(record)
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
    
    return data

def explore_multiple_files(data_dir, max_files=50):
    """Explore multiple files to get better statistics"""
    all_data = []
    jsonl_files = [f for f in os.listdir(data_dir) if f.endswith('.jsonl.gz')]
    
    print(f"Found {len(jsonl_files)} files in directory")
    print(f"Processing first {max_files} files...")
    
    for i, filename in enumerate(jsonl_files[:max_files]):
        filepath = os.path.join(data_dir, filename)
        file_data = load_complete_fireball_file(filepath)
        all_data.extend(file_data)
        
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{max_files} files...")
    
    df = pd.DataFrame(all_data)
    print(f"✅ Loaded {len(df)} total records from {max_files} files")
    return df

def comprehensive_analysis(df):
    """Comprehensive analysis of the loaded dataset"""
    
    print("=" * 70)
    print("COMPREHENSIVE FIREBALL DATASET ANALYSIS")
    print("=" * 70)
    
    print(f"📊 Total records: {len(df):,}")
    print(f"📝 Total columns: {len(df.columns)}")
    
    # Analyze commands across all records
    print("\n" + "=" * 50)
    print("COMMAND ANALYSIS")
    print("=" * 50)
    
    all_commands = []
    for commands in df['commands_norm'].dropna():
        all_commands.extend(commands)
    
    command_counts = Counter(all_commands)
    print(f"Total unique commands: {len(command_counts)}")
    print(f"Total command instances: {len(all_commands)}")
    print("\nTop 20 most common commands:")
    for cmd, count in command_counts.most_common(20):
        print(f"  {cmd}: {count} times")
    
    # Analyze utterance patterns - FIXED VERSION
    print("\n" + "=" * 50)
    print("UTTERANCE ANALYSIS")
    print("=" * 50)
    
    before_utterances = df['before_utterances'].apply(lambda x: len(x) if x else 0)
    after_utterances = df['after_utterances'].apply(lambda x: len(x) if x else 0)
    
    print(f"Records with before_utterances: {(before_utterances > 0).sum()}")
    print(f"Records with after_utterances: {(after_utterances > 0).sum()}")
    print(f"Average before_utterances per record: {before_utterances.mean():.2f}")
    print(f"Average after_utterances per record: {after_utterances.mean():.2f}")
    
    # FIXED: Show examples of utterances
    print("\nExamples of before_utterances:")
    utterance_examples = df[df['before_utterances'].apply(lambda x: len(x) > 0 if x else False)]['before_utterances'].head(3)
    for i, utterances in enumerate(utterance_examples):
        print(f"Example {i+1}:")
        for utterance in utterances[:3]:  # Show first 3 utterances max
            print(f"  - {utterance}")
    
    # Analyze combat states
    print("\n" + "=" * 50)
    print("COMBAT STATE ANALYSIS")
    print("=" * 50)
    
    combat_actors = []
    for state in df['combat_state_before'].dropna():
        combat_actors.extend(state)
    
    if combat_actors:
        actors_df = pd.DataFrame(combat_actors)
        print(f"Total combat actor appearances: {len(actors_df):,}")
        print(f"Unique actor names: {actors_df['name'].nunique()}")
        
        print("\nTop 10 most common actors:")
        print(actors_df['name'].value_counts().head(10))
        
        # Analyze classes
        valid_classes = actors_df['class'].dropna()
        if len(valid_classes) > 0:
            print(f"\nUnique classes: {valid_classes.nunique()}")
            print("Most common classes:")
            print(valid_classes.value_counts().head(10))
    else:
        print("No combat state data found.")
    
    return df, command_counts

# Usage - process multiple files
data_dir = "C:/Users/Eliza/Downloads/Test Dataset AI/anonymized/filtered"
df = explore_multiple_files(data_dir, max_files=50)  # Process 50 files for better stats
df, command_counts = comprehensive_analysis(df)

#------------------------------------------------------------------------------------------

def estimate_total_dataset_size(data_dir, sample_size=100):
    """Estimate the total size of the dataset without loading everything"""
    jsonl_files = [f for f in os.listdir(data_dir) if f.endswith('.jsonl.gz')]
    sample_files = jsonl_files[:sample_size]
    
    total_records = 0
    total_commands = 0
    total_with_narration = 0
    
    print(f"Sampling {len(sample_files)} files to estimate dataset size...")
    
    for i, filename in enumerate(sample_files):
        filepath = os.path.join(data_dir, filename)
        records = load_complete_fireball_file(filepath)
        total_records += len(records)
        
        for record in records:
            if record.get('commands_norm'):
                total_commands += len(record['commands_norm'])
            if record.get('after_utterances'):
                total_with_narration += 1
        
        if (i + 1) % 20 == 0:
            print(f"Sampled {i + 1} files...")
    
    # Extrapolate to full dataset
    avg_records_per_file = total_records / len(sample_files)
    estimated_total_records = avg_records_per_file * len(jsonl_files)
    estimated_total_commands = (total_commands / len(sample_files)) * len(jsonl_files)
    
    print("\n" + "=" * 60)
    print("DATASET SIZE ESTIMATION")
    print("=" * 60)
    print(f"Files sampled: {len(sample_files)}")
    print(f"Total files in dataset: {len(jsonl_files):,}")
    print(f"Average records per file: {avg_records_per_file:.2f}")
    print(f"Estimated total records: {estimated_total_records:,.0f}")
    print(f"Estimated total commands: {estimated_total_commands:,.0f}")
    print(f"Records with narration in sample: {total_with_narration}/{total_records} ({total_with_narration/total_records*100:.1f}%)")
    
    return estimated_total_records

# Run the estimation
estimated_size = estimate_total_dataset_size(data_dir)

#------------------------------------------------------------------------------------------
def create_high_quality_training_pairs(df, min_quality_score=2):
    """
    Create training pairs focusing on high-quality examples
    Quality score based on:
    - Has commands (1 point)
    - Has before_utterances (1 point) 
    - Has after_utterances (2 points)
    - Has automation_results (1 point)
    """
    training_pairs = []
    
    for idx, row in df.iterrows():
        quality_score = 0
        
        # Calculate quality score
        if row.get('commands_norm'):
            quality_score += 1
        if row.get('before_utterances') and len(row['before_utterances']) > 0:
            quality_score += 1
        if row.get('after_utterances') and len(row['after_utterances']) > 0:
            quality_score += 2
        if row.get('automation_results'):
            quality_score += 1
        
#            if quality_score >= min_quality_score:
#                input_text = create_dm_input_prompt(
#                    row.get('combat_state_before', []),
#                    row.get('before_utterances', []),
#                    row.get('utterance_history', []),
#                    row.get('current_actor', {})
#                )
                
#                output_text = create_dm_output(
#                    row.get('commands_norm', []),
#                    row.get('automation_results', []),
#                    row.get('after_utterances', [])
#                )
                
#                if input_text and output_text:
#                    training_pairs.append({
#                        "input": input_text,
#                        "output": output_text,
#                        "quality_score": quality_score
#                    })
    
    print(f"Created {len(training_pairs)} training pairs (quality score ≥ {min_quality_score})")
    return training_pairs

def process_dataset_in_batches(data_dir, output_file="training_data.jsonl", batch_size=1000, max_files=5000):
    """Process dataset in batches to manage memory"""
    jsonl_files = [f for f in os.listdir(data_dir) if f.endswith('.jsonl.gz')]
    jsonl_files = jsonl_files[:max_files]  # Limit for initial training
    
    all_training_pairs = []
    
    for batch_start in range(0, len(jsonl_files), batch_size):
        batch_files = jsonl_files[batch_start:batch_start + batch_size]
        batch_data = []
        
        print(f"Processing batch {batch_start//batch_size + 1}/{(len(jsonl_files)-1)//batch_size + 1}...")
        
        for filename in batch_files:
            filepath = os.path.join(data_dir, filename)
            file_data = load_complete_fireball_file(filepath)
            batch_data.extend(file_data)
        
        df_batch = pd.DataFrame(batch_data)
        batch_pairs = create_high_quality_training_pairs(df_batch)
        all_training_pairs.extend(batch_pairs)
        
        print(f"  → Added {len(batch_pairs)} pairs (Total: {len(all_training_pairs)})")
        
        # Save progress every batch
        with open(f"training_data_batch_{batch_start//batch_size + 1}.jsonl", 'w', encoding='utf-8') as f:
            for pair in batch_pairs:
                f.write(json.dumps(pair) + '\n')
    
    # Save final combined file
    with open(output_file, 'w', encoding='utf-8') as f:
        for pair in all_training_pairs:
            f.write(json.dumps(pair) + '\n')
    
    print(f"\n✅ Final dataset: {len(all_training_pairs)} training pairs")
    return all_training_pairs

# Run the batch processing
training_data = process_dataset_in_batches(data_dir, max_files=1000)  # Start with 1000 files