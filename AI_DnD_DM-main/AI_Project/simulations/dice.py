import random
import re


def roll_die(sides: int) -> int:
    """Roll a single die with ``sides`` faces and return the result."""

    if sides < 2:
        raise ValueError("Dice must have at least 2 sides.")
    return random.randint(1, sides)


def roll_d20(advantage_state: str = "normal") -> tuple[int, list[int]]:
    """Roll a d20 honouring advantage/disadvantage rules.

    Returns a tuple of ``(kept_result, all_rolls)``.
    """

    advantage_state = (advantage_state or "normal").lower()
    if advantage_state == "advantage":
        rolls = [roll_die(20), roll_die(20)]
        return max(rolls), rolls
    if advantage_state == "disadvantage":
        rolls = [roll_die(20), roll_die(20)]
        return min(rolls), rolls
    result = roll_die(20)
    return result, [result]

def roll_dice(dice_string):

    """
    Simulates rolling dice based on standard D&D notation.

    Args:
        dice_string (str): A string in the format 'NdS[+/-]M', where:
                         - N: number of dice (optional, defaults to 1)
                         - S: number of sides on the die
                         - M: modifier (optional, can be positive or negative)

    Returns:
        int: The total result of the dice roll plus the modifier.

    Examples:
        >>> roll_dice("1d20")
        # Rolls 1 twenty-sided die
        >>> roll_dice("2d6+3")
        # Rolls 2 six-sided dice, sums them, and adds 3
        >>> roll_dice("d8-1")
        # Rolls 1 eight-sided die and subtracts 1
        >>> roll_dice("4d10")
        # Rolls 4 ten-sided dice
    """
    
    #Default values if parts are missing
    num_dice = 1
    modifier = 0
    
    #Use regular expression to parse the dice string
    #This pattern matches: (optional number)d(number)(optional +- modifier)
    pattern = r'^(\d*)d(\d+)([+-]\d+)?$'
    match = re.match(pattern, dice_string)
    
    if not match:
        raise ValueError(f"Invalid dice format: '{dice_string}'. Use format like '2d6+3' or 'd20'.")
    
    #Extract parts from the regex match
    num_dice_str, sides_str, modifier_str = match.groups()
    
    #Convert the extracted strings to integers, handling empty values
    num_dice = int(num_dice_str) if num_dice_str else 1
    sides = int(sides_str)
    if modifier_str:
        modifier = int(modifier_str)  #This handles both + and - signs
    
    #Validate the values
    if num_dice < 1:
        raise ValueError("Number of dice must be at least 1.")
    if sides < 2:
        raise ValueError("Dice must have at least 2 sides.")
    
    #Roll the dice!
    total = 0
    for _ in range(num_dice):
        roll = roll_die(sides)
        total += roll
    
    #Apply the modifier
    total += modifier
    
    return total

#Example usage and test function
def test_dice_roller():
    """Test function to verify the dice roller works correctly."""
    print("Testing dice roller...")
    
    #Test cases with expected range of results
    test_cases = [
        ("1d20", (1, 20)),
        ("2d6+3", (5, 15)),  #min: 2*1+3=5, max: 2*6+3=15
        ("d8-1", (0, 7)),    #min: 1-1=0, max: 8-1=7
        ("4d10", (4, 40)),
        ("3d4-2", (1, 10)),  #min: 3*1-2=1, max: 3*4-2=10
    ]
    
    for dice_str, (min_val, max_val) in test_cases:
        #Roll multiple times to check it stays within bounds
        for _ in range(10):
            result = roll_dice(dice_str)
            if result < min_val or result > max_val:
                print(f"ERROR: {dice_str} produced {result}, expected between {min_val}-{max_val}")
                return False
        
        print(f"✓ {dice_str} consistently in range {min_val}-{max_val}")
    
    #Test error handling
    try:
        roll_dice("invalid")
        print("ERROR: Should have raised ValueError for invalid format")
        return False
    except ValueError:
        print("✓ Correctly handled invalid dice format")
    
    try:
        roll_dice("0d6")  #Invalid number of dice
        print("ERROR: Should have raised ValueError for 0 dice")
        return False
    except ValueError:
        print("✓ Correctly handled 0 dice")
    
    print("All tests passed!")
    return True

#If this file is run directly, run the tests
if __name__ == "__main__":
    test_dice_roller()