import random
print("Rock Paper Scissors")
print("Game Rules \n 1. Rock Vs Paper --> Paper Wins\n 2. Rock Vs Scissors --> Rock Wins\n 3. Paper Vs Scissors --> Scissor Wins")
ass_num = {1:"Rock",2:"Paper",3:"Scissors"}
name = input("Enter Your Name : ")
print("Start your Game\n Choose 1.Rock 2.Paper 3.Scissors")
play=True
while play==True:
    choice = int(input("Enter Your Choice(1/2/3): "))
    
    rand_num = random.randint(1,3)
    print(f"Your Choice:{ass_num[choice]},Computer Choice:{ass_num[rand_num]}")
    result = ""
    if choice == rand_num :
        result = 0
    elif (choice == 1 and rand_num == 2) or (choice == 2 and rand_num == 1):
        result =2
    elif (choice == 1 and rand_num == 3) or (choice == 3 and rand_num == 1):
        result =1
    elif (choice == 2 and rand_num == 3) or (choice == 3 and rand_num == 2):
        result =3
    else:
        print("To be Written")
    if result == 0:
        print("Draw!")
    elif choice == result:
            print(f"{name} wins!")
    else:
        print("Computer Wins!")
    play_again = input("Do you want to play again(y/n):").lower()
    if play_again == "y":
        play=True
    else:
        play=False
        break

print("Thanks")