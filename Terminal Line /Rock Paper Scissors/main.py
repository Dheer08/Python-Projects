import random

choices = {1: "Rock", 2: "Paper", 3: "Scissors"}

def get_winner(user, comp):
    if user == comp:
        return "draw"
    elif (user - comp) % 3 == 1:
        return "user"
    else:
        return "computer"

def impossible_move(user):
    # Computer always picks the winning move
    return (user % 3) + 1

print("🎮 Rock Paper Scissors")
name = input("Enter Your Name: ")

while True:
    print("\nSelect Game Mode:")
    print("1. Normal")
    print("2. No Draw")
    print("3. Impossible 😈")

    try:
        mode = int(input("Enter mode (1/2/3): "))
        if mode not in [1, 2, 3]:
            print("Invalid mode!")
            continue
    except ValueError:
        print("Enter a valid number!")
        continue

    while True:
        try:
            user = int(input("\nChoose (1: Rock, 2: Paper, 3: Scissors): "))
            if user not in choices:
                print("Invalid choice!")
                continue
        except ValueError:
            print("Enter a number!")
            continue

        # Mode logic
        if mode == 3:
            comp = impossible_move(user)
        else:
            comp = random.randint(1, 3)

        print(f"{name}: {choices[user]}")
        print(f"Computer: {choices[comp]}")

        result = get_winner(user, comp)

        # Mode-specific behavior
        if result == "draw":
            if mode == 2:
                print("Draw! Replaying round...")
                continue
            else:
                print("It's a Draw!")
        elif result == "user":
            print(f"{name} Wins!")
        else:
            print("Computer Wins!")

        break  # Exit round loop

    play_again = input("\nPlay again? (y/n): ").lower()
    if play_again != 'y':
        break

print("Thanks for playing!")