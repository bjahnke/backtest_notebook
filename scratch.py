from dataclasses import dataclass
import sys
from typing import Literal
print(sys.version)
import tkinter

amountOfPlayers = 2
handCount = 0
cards = []
cardSuit = ""
cardRank = ""
hand = []
image_listHand = []
back_imageList = []
button_list = []
money = [1000, 1000]

def getPlayerMoney(index):
    return str(money[index])

def loadMoney():
    '''Loads the money into each of the players hands'''
    global potValue
    potValue = int(potEntry.get())
    for i in range(amountOfPlayers):
        money.append(potValue)
    potEntry.destroy()

#This deals the card to each of the players
def dealCard():
   '''Deals the Card to Each of the players'''
   global handCount, cards, cardSuit, cardRank, hand
   for i in range(amountOfPlayers):
       hand = []
       while handCount < 2:
           backImage = backImage.resize((75, 100))
           back_imageList.append(backImage)
           cardButton = tkinter.Button(canvas, image = backImage, text = "0", compound = "bottom", command = lambda index = image_listHand.index(cardImage): [flipImage(index)])
           cardButton.config(text = lambda index = i: [getPlayerMoney(index)])
           button_list.append(cardButton)
           cardButton.place(x = (-25 * amountOfPlayers) + (50*(2*i+1) + 120*(i + 1)) + (handCount + 1)*80, y = (300))
           handCount = handCount + 1
           hand.append(card)
       cards.append(hand)
       handCount = 0 

def display():
    return 0

def main ():
    root = tkinter.Tk()
    root.title("Hello, Tkinter!")
    root.geometry("400x200")

    button = tkinter.Button(root, text="Click me!")
    button.config(text = display())
    button.config
    button.pack()

    root.mainloop()

if __name__ == "__main__":
    main()

@dataclass
class ContactName:
    id: str
    parent_name: str

@dataclass
class ContactTable:
    id: str

@dataclass
class ContactEmail:
    id: str
    email: str
    contact_name_id='' # foreign key to ContactName

@dataclass
class ContactPhonePriority:
    id: str
    contact_phone_id: str # foreign key to ContactPhone

@dataclass
class ContactPhone:
    id: str
    phone: str
    type: Literal['workphone', 'cell']

@dataclass
class ContactName_ContactTable:
    id=''
    contact_name_id=''
    contact_table_id=''