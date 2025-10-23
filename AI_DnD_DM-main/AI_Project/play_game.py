from game_engine import DnDGameEngine

def main():
    print("🎲 D&D AI DUNGEON MASTER")
    print("="*60)
    
    # Initialize game with your trained model
    game = DnDGameEngine("./dm_working")  # Path to your trained model
    
    # Start new game sequence
    game.start_game_sequence()
    
    # Main game loop
    while True:
        state = game.get_visible_game_state()
        
        # Display game state
        print(f"\n{'═' * 60}")
        if state['combat_active']:
            print(f"⚔️  COMBAT - Round {state['round']} | Turn: {state['current_turn']}")
        else:
            print(f"🌄 {state['environment']} | Current: {state['current_turn']}")
        
        print("\n🎭 HEROES:")
        for char in state['characters']:
            hp_status = f"{char['hit_points']}/{char['max_hit_points']} HP"
            if char['hit_points'] <= 0:
                hp_status = "💀 UNCONSCIOUS"
            elif char['hit_points'] < char['max_hit_points'] * 0.5:
                hp_status = f"🩸 {hp_status}"
            print(f"  {char['name']} ({char['class']}) - {hp_status} | AC: {char['armor_class']}")
        
        if state['monsters']:
            print("\n🐉 MONSTERS:")
            for monster in state['monsters']:
                hp_status = f"{monster['hp']}/{monster['max_hp']} HP"
                if monster['hp'] <= 0:
                    hp_status = "💀 DEFEATED"
                elif monster['hp'] < monster['max_hp'] * 0.5:
                    hp_status = f"🩸 {hp_status}"
                print(f"  {monster['name']} - {hp_status} | AC: {monster['armor_class']}")
        
        print('═' * 60)
        
        # Check for game end conditions
        if not state['characters']:
            print("\n💀 GAME OVER - All heroes have fallen!")
            break
            
        if not state['monsters'] and state['combat_active']:
            print("\n🎉 VICTORY! All monsters defeated!")
            break
        
        # Get player action
        current_player = state['current_turn']
        player = input(f"\n{current_player}, what do you do? ").strip()
        
        if player.lower() in ['quit', 'exit', 'end']:
            print("Thanks for playing!")
            break
        
        if not player:
            continue
        
        # Process action
        try:
            result = game.process_player_action(current_player, player)
            
            # Display results
            print(f"\n🎭 {result['player']}: {result['action']}")
            print(f"🧙‍♂️ DM: {result['dm_narration']}")
            
            if result['command_results']:
                print(f"⚡ System: {' | '.join(result['command_results'])}")
                
        except Exception as e:
            print(f"❌ Error processing action: {e}")
            print("Please try a different action.")
    
    # End game summary
    print("\n" + "="*60)
    print("🏁 GAME SUMMARY")
    print("="*60)
    final_state = game.get_visible_game_state()
    
    print("Final Status:")
    for char in final_state['characters']:
        status = "ALIVE" if char['hit_points'] > 0 else "DEFEATED"
        print(f"  {char['name']}: {status} ({char['hit_points']}/{char['max_hit_points']} HP)")
    
    if final_state['monsters']:
        print("Remaining Monsters:")
        for monster in final_state['monsters']:
            status = "ALIVE" if monster['hp'] > 0 else "DEFEATED"
            print(f"  {monster['name']}: {status}")

if __name__ == "__main__":
    main()