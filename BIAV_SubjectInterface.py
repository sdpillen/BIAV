'''Despite the script name, this is the Brain In A Vat (BIAV) script.  This is to be used when the subjects demonstrate an 85% or higher performance off of
TMA-cued neurofeedback.  Direct all love, hate, or idle curiosity to Steven Pillen (SP) at stevendpillen@gmail.com.  He will also accept pictures of crows.'''

import pygame, sys
from pygame.locals import * 
import numpy as np
import time
import CCDLUtil.MagStimRapid2Interface.ArmAndFire as CCDLtms
from random import randrange #for starfield, random number generator
print("Initializing the Neurofeedback Paradigm...")

'''As stated in other files,.  These global variables probably should have been
defined in a configuration file.  If I had more time... I still probably wouldn't have gotten around to it, because there's always
a more pressing matter, isn't there?  Regardless, take stock of the HIGH_INTENSITY and LOW_INTENSITY variables.  Hardcode these values
according to the TMS threshold of your subjects.  I recommend leaving everything else alone unless you have a good reason. -SP'''


#For debugging NFT; is updated live by visualizer.py.
DISCONNECT = False
LastDISCONNECT = False  #so current and previous states can be compared

'''THESE VALUES ARE CRITICAL.  The top value indicates whether the script will be sending TMS pulses, which by default, it should.
Likewise, the HIGH_INTENSITY and LOW are the values that have been determined to either reliably elicit, or not elicit phosphenes. -SP'''

FIRE_TMS_FLAG = True        #can be set to false for debugging
HIGH_INTENSITY = 85         #High TMS pulse value for phosphene
LOW_INTENSITY = 35          #Low TMS pulse value for no phosphene

# Number of frames per second
# This value doesn't really need to be high for this script.  20 is sufficient
FPS = 20

#Alpha can be toggled with a button on the Visualizer console
alpha = False

#Submit is a flag for when a maze is submitted
Submit = False


'''These values are the time periods used in the paradigm.  It may be necessary to alter these to be more forgiving if
subjects fail to perform at about 85% levels during the TMS-guided trials. -SP'''

leftrightperiod = 20    #20 seconds for responses to left or right
poststimperiod = 5      #5 seconds buffer after a stim
answerperiod = 20       #20 seconds to answer the non alternating left/right
leftrightbuffer = 10    #10 seconds as a buffer after answering left/right
mazebuffer = 5          #5 seconds before switching to the maze selection screen
postmazebuffer = 8      #8 seconds after a maze is submitted before the next stim
tempbuffer = 10         #10 seconds in a temporary buffer that was added for debugging purposes

#Funny variable
CustomName = False




#The default filenames for the paradigm:
OutputFilename = 'NFT_MetaData.csv'     #this contains information about the performance of the subject
TS = 'NFT_TS.csv'                       #This is the timestamps of key events

pygame.display.init()   #Display functions are used for visualizing the game.  this initializes the display

disp = pygame.display.Info()    #initialization step for display; generates some static variables
WINDOWWIDTH = disp.current_w    #I like the screen slightly smaller than window size for ease of portability
WINDOWHEIGHT = disp.current_h   #no need to modify the actual width
size = [WINDOWWIDTH,WINDOWHEIGHT]   #This is the dimensions of the screen display

'''DEBUG Defaults  (these can be ignored if you aren't doing anything exotic, such as running the paradigm without any actual NFT data passing through) -SP'''
deviance = 0.5      #DEBUG default for stdev of target Hz baseline data
HiDev = 0.5         #DEBUG default for stdev of Hi noise freq baseline data
LoDev = 0.5         #DEBUG default for stdev of Lo noise freq baseline data
Threshold = 1.0     #EEG threshold for changing NFT parameter
HiNoise = 1.0       #High amplitude noise amplitude; Dummy value for the electrode
LoNoise = 1.0       #Low amplitude noise; Dummy value for the electrode
TargetVal = 0        #Signal amplitude; Dummy value for the electrode
SPTruVal = 0        #Value that gets exported from the visualizer



'''It's an inelegant solution, but the BlocInterval is set arbitrarily high so as to make it unnecessary to reconfigure the rounds which are now governed by
number of stimuli, based on modified code that was oriented around timed trials.  Perhaps some day, someone will see fit to put proper "if" conditionals
to specify these  things and remove this unsightly variable.  But, that person is not me.  Not today, anyway.  Not for lack of desire, but for lack of time. -SP'''
#These are the time intervals for the training in seconds.
BlocInterval = 110000    #300
FixationInterval = 15 #180 #This is extended by 9 seconds as a bandaid solution to the fact that the timing is misaligned between both paradigms.  A problem for later, I think.
if alpha == True:
    FixationInterval = 100
#Flags for high and low noise; false until noise thresholds are passed.
HighNoiseFlag = False
LowNoiseFlag = False


'''Take note of the fact that there are 3 series of values ranging 1-8.  These are the final outcomes of the mazes.  In other words, there are a grand total of 
24 true mazes, and each outcome occurs 3 times, randomly.  Unlike in the NFt paradigm, there is nothing to guarantee a certain level of randomness one way or another.
Note also the Sham: it will be inserted somewhere after the "numbers" have been shuffled in a multiple of 8.  This guarantees there will be 8 non-repeating values
for the sham round.-SP'''
#numbers
numbers = [1,2,3,4,5,6,7,8,1,2,3,4,5,6,7,8,1,2,3,4,5,6,7,8] #There are 24 values here, 3 repeated counts to 8
sham = [1,2,3,4,5,6,7,8]    #8 numbers in the control round.  don't want repeats

stimarray = [0,0,0,0,0,1,1,1,1,1]   #This is the array for stimulation during the blind TMS-guided NFT
np.random.shuffle(stimarray)        #This randomizes the values for the blind TMS-guided NFT

np.random.shuffle(numbers)  #This shuffles the true TMS Maze rounds
np.random.shuffle(sham)     #this shuffles the control mazes
numbers = numbers + sham    #maze lists can be concatenated.  "numbers[1:x] + sham + numbers[x:end]" works for inserting in the middle
shamround = 4 #this is referenced so the subject is not alerted which of the 4 maze blocks is the sham, but you are.  
'''^^^Please note that the shamround is a value yo will want to specify^^^'''

#this lets us know from the getgo what the maze array is
print 'numbers are ', numbers, ' and stims are ', stimarray


'''These are the initial values of the mazes.  The maze has 3 aspects, each of which is governed here.
I will expand on the role of these numbers when they are pertinent, but for right now, just think of it as a decision tree with 4 branching points.'''
maze = 0        #this is which maze we are using
branch = 0      #this is whether we are stimming, collecting data, or somewhere in between
substage = 0    #this mostly governs which part of the maze response section we are in
stage = 0

#Debug flag displays sometimes useful information when set to "true" by hitting D
DebugFlag = False


resultsarray = []   
NEXT = False        #This flag switches rounds at the pause point when set to true through the GUI interface
Record = False      #This flag determines whether EEG is being recorded.  Gets set to True at the baseline and remains true until the end of the experiment


#The number of pixels in pygame line functions, by default
LINETHICKNESS = 10  

#Initialize the sound engine then load a sound
pygame.mixer.init()
coin = pygame.mixer.Sound('mariocoin.wav') 

# Set up the colours (RGB values). static variables
BLACK     = (0  ,0  ,0  )
GREY      = (190  ,190  ,190  )
WHITE     = (255,255,255)
YELLOW    = (255,255,0)
ORANGE    = (255,165,0)
RED       = (255,0,0)
CYAN      = ( 52, 221, 221)
BLUE      = (0, 95, 235)
VIOLET    = (128,0,128)


TEXTCOLOR = BLACK


#Baselining variable declarations; largely artifactual. will be phased out in future revisions, assuming they happen.
output = 0
HiOutput = 0
LoOutput = 0
consolidatedoutput = []
consolidatedhi = []
consolidatedlo = []







''' This function draws and colors the reticle as is appropriate for the stage of a given round. 
    This means it shifts to RED when it's nearly time for stimulation (real or simulated), and 
    that it shifts to BLUE when it's time for the participant to respond as best as they can. -SP '''
def reticle(color):
    pygame.draw.line(DISPLAYSURF, color, ((WINDOWWIDTH/2-20), WINDOWHEIGHT/2-40),((WINDOWWIDTH/2-20),WINDOWHEIGHT/2+40), (int(LINETHICKNESS*1.5)))
    pygame.draw.line(DISPLAYSURF, color, ((WINDOWWIDTH/2-60), WINDOWHEIGHT/2),((WINDOWWIDTH/2 + 20),WINDOWHEIGHT/2), (int(LINETHICKNESS*1.5)))

''' This is both the initial prompt and the breaks between blocks.  This basic structure has governed NFT of my design since 
    the days of Emotiv.  I am still struck with the feeling that this could have been done more elegantly.  Regardless, I have
    hijacked my own questionable design decisions with more questionable design decisions to integrate a method of displaying
    instructions into the script.  It is important to be able to reinvent yourself as the times demand.  -SP'''
def Pausepoint(stage, score):


    #
    global submitbutton
    
    
    #grey out everything on the screen
    DISPLAYSURF.fill(GREY)

    #these variables are used in the main function and this is easier than passing them.
    #in .main(), these are all defined as images loaded from files of the same name, 
    #i.e. "Stage1.png" in the base directory of BIAV
    global Stage1
    global Stage2
    global Stage3
    global Stage4
    global Stage4_1
    global Stage4_2
    global Stage5
    
    

    
    
    '''This portion of the script is responsible for displaying the instructions for given stages.  Notice that the DISPLAYSURF.blit functions are showing image files.
    If you want to change the instructions at any stage, you must change the Stage.png images that correspond to each.  This is as simple as using your image manipulation
    software of choice; even clunky old paint will do the trick, if you are desperate or atavistically eccentric.  -SP'''
    
    if stage == 0:  #Stage 0 is the pre-baseline state.  
        if time.time() < initialization: #a 5 second delay, which is what initialization is, helps things go more smoothly
            resultSurf = SCOREFONT.render('Please wait while initializing.', True, TEXTCOLOR) 
        else:
            resultSurf = SCOREFONT.render('Start recording to begin baseline.', True, TEXTCOLOR)
            DISPLAYSURF.blit(Stage1.image, Stage1.rect) #This image, stage1.image, 
            
    #the scorefont.render portions are all just the title text in the screens.  
    if stage == 1:  #stage 1 should be the calibration round.
        resultSurf = SCOREFONT.render('Neurofeedback Calibration', True, TEXTCOLOR) #this sets up the title text
        DISPLAYSURF.blit(Stage2.image, Stage2.rect)    #this prints the instruction image to the screen   
    if stage == 2: 
        resultSurf = SCOREFONT.render('Unseen Neurofeedback', True, TEXTCOLOR)
        DISPLAYSURF.blit(Stage3.image, Stage3.rect)
    if stage == 3:
        resultSurf = SCOREFONT.render('TMS-Guided Neurofeedback', True, TEXTCOLOR)
        DISPLAYSURF.blit(Stage4.image, Stage4.rect)
    if stage == 4:
        resultSurf = SCOREFONT.render('Mazes: Round 1 of 4', True, TEXTCOLOR)
        DISPLAYSURF.blit(Stage4_1.image, Stage5.rect)
    if stage == 4.1:
        resultSurf = SCOREFONT.render('Mazes: Round 1 of 4', True, TEXTCOLOR)
        DISPLAYSURF.blit(Stage4_2.image, Stage5.rect)
        
        
    ''' here on out is the pauses before the Mazes rounds.  Take note of the condition
        which prints out a warning about the sham round.  this is your sign that the time has come 
        to misalign the TMS wand so that you are not actually targetting the brain. -SP'''  
    if stage == 4.2:
        resultSurf = SCOREFONT.render('Mazes: Round 1 of 4', True, TEXTCOLOR)
        DISPLAYSURF.blit(Stage5.image, Stage5.rect)
        if shamround == 1:
            print 'this is the sham round'      #this spams at the break before the "sham round" if this is the sham round
    if stage == 5:
        resultSurf = SCOREFONT.render('Mazes: Round 2 of 4', True, TEXTCOLOR)
        DISPLAYSURF.blit(Stage5.image, Stage5.rect)
        if shamround == 2:
            print 'this is the sham round'      #this spams at the break before the "sham round"        
    if stage == 6:
        resultSurf = SCOREFONT.render('Mazes: Round 3 of 4', True, TEXTCOLOR)
        DISPLAYSURF.blit(Stage5.image, Stage5.rect)
        if shamround == 3:
            print 'this is the sham round'      #this spams at the break before the "sham round"        
    if stage == 7:
        resultSurf = SCOREFONT.render('Mazes: Round 4 of 4', True, TEXTCOLOR)
        if shamround == 4:
            print 'this is the sham round'      #this spams at the break before the "sham round"
        DISPLAYSURF.blit(Stage5.image, Stage5.rect)  
        
    #This displays the title  text    
    resultRect = resultSurf.get_rect()
    resultRect.center = (WINDOWWIDTH/2, 100)    #this positions the "scorefont" text top and center
    DISPLAYSURF.blit(resultSurf, resultRect)    #This is the image
    
    
    

    
        
    
#BASELINING FIXATION CROSS.  Clears all out and displays a black cross.
def fixation(recordtick):
    #Clear the screen
    DISPLAYSURF.fill(GREY)
    #Draw the reticle
    reticle(TEXTCOLOR)
 

#Draws the arena the game will be played in.  Unused for now, could be populated if useful later
def drawArena():
    DISPLAYSURF.fill(GREY)
    reticle(TEXTCOLOR)
  

'''draws a sprite for the circle.  this function was originally used for the glider, but a circle is more appropriate here. -SP'''
def drawSprite(b):  
    #Stops it from going too far left
    if b.rect.right > WINDOWWIDTH - LINETHICKNESS + 90:
        b.rect.right = WINDOWWIDTH - LINETHICKNESS + 90
    #Stops sprite moving too far right 
    elif b.rect.left < LINETHICKNESS:
        b.rect.left = LINETHICKNESS
    DISPLAYSURF.blit(b.image, b.rect) #this draws the image onto the display surface

    
    
	
'''Displays debugging stuff; this can largely be ignored, unless you want something to be displayed when hitting "d".
    I recommend doing this if something seems off while running an experiment, and you were about ready to kill
    the process anyways.  Assuming it isn't just completely nonresponsive.  -SP'''
def displayDEBUG(TargetVal):
    global VoltMax
    global VoltMin
    global VoltBaseline
    resultSurf = BASICFONT.render('nothing', True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 300, 25)
    DISPLAYSURF.blit(resultSurf, resultRect)
    resultSurf = BASICFONT.render('nothing', True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 300, 40)
    DISPLAYSURF.blit(resultSurf, resultRect)
    if FirstSuccessFlag == True:
        resultSurf = BASICFONT.render('Fst+', True, TEXTCOLOR)
        resultRect = resultSurf.get_rect()
        resultRect.topleft = (WINDOWWIDTH - 300, 55)
        DISPLAYSURF.blit(resultSurf, resultRect)
    if ContinualSuccessFlag == True:
        resultSurf = BASICFONT.render('Cnt+', True, TEXTCOLOR)
        resultRect = resultSurf.get_rect()
        resultRect.topleft = (WINDOWWIDTH - 375, 55)
        DISPLAYSURF.blit(resultSurf, resultRect)
    if HighNoiseFlag == True:
        resultSurf = BASICFONT.render('hinoi', True, ORANGE)
        resultRect = resultSurf.get_rect()
        resultRect.topleft = (WINDOWWIDTH - 300, 70)
        DISPLAYSURF.blit(resultSurf, resultRect)
    if LowNoiseFlag == True:
        resultSurf = BASICFONT.render('lonoi', True, RED)
        resultRect = resultSurf.get_rect()
        resultRect.topleft = (WINDOWWIDTH - 375, 70)
        DISPLAYSURF.blit(resultSurf, resultRect)  
    resultSurf = BASICFONT.render('LNoi = %s' %(round(LoNoise,1)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 85)
    DISPLAYSURF.blit(resultSurf, resultRect)
    resultSurf = BASICFONT.render('LNoTh = %s' %(round(LoOutput,1)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 100)
    DISPLAYSURF.blit(resultSurf, resultRect)
    resultSurf = BASICFONT.render('Lnxt = %s' %(len(consolidatedloNext)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 115)
    DISPLAYSURF.blit(resultSurf, resultRect)
    
    resultSurf = BASICFONT.render('HNoi = %s' %(round(HiNoise,1)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 145)
    DISPLAYSURF.blit(resultSurf, resultRect)
    resultSurf = BASICFONT.render('HNoTh = %s' %(round(HiOutput,1)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 160)
    DISPLAYSURF.blit(resultSurf, resultRect)
    resultSurf = BASICFONT.render('Hnxt = %s' %(len(consolidatedhiNext)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 175)
    DISPLAYSURF.blit(resultSurf, resultRect)
    
    resultSurf = BASICFONT.render('stage = %s' %(stage), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 190)
    DISPLAYSURF.blit(resultSurf, resultRect)
    
    
    resultSurf = BASICFONT.render('Sign = %s' %(round(TargetVal,3)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 220)
    DISPLAYSURF.blit(resultSurf, resultRect)
    resultSurf = BASICFONT.render('Thr = %s' %(round(Threshold,1)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 235)
    DISPLAYSURF.blit(resultSurf, resultRect)
    resultSurf = BASICFONT.render('Snxt = %s' %(len(consolidatedoutputNext)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect() 
    resultRect.topleft = (WINDOWWIDTH - 165, 250)
    DISPLAYSURF.blit(resultSurf, resultRect)
    
    resultSurf = BASICFONT.render('nothing', True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 280)
    DISPLAYSURF.blit(resultSurf, resultRect)
    
    resultSurf = BASICFONT.render('sJar = %s' %(round(time.time() - successjar, 1)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 295)
    DISPLAYSURF.blit(resultSurf, resultRect)
    
    resultSurf = BASICFONT.render('Time = %s' %(round(time.time() - countdown, 1)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 310)
    DISPLAYSURF.blit(resultSurf, resultRect)
    
    resultSurf = BASICFONT.render('VMin = %s' %(round(VoltMin, 1)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 340)
    DISPLAYSURF.blit(resultSurf, resultRect)
    
    resultSurf = BASICFONT.render('Vmax = %s' %(round(VoltMax, 1)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 360)
    DISPLAYSURF.blit(resultSurf, resultRect)

    resultSurf = BASICFONT.render('VBas = %s' %(round(VoltBaseline, 1)), True, TEXTCOLOR)
    resultRect = resultSurf.get_rect()
    resultRect.topleft = (WINDOWWIDTH - 165, 380)
    DISPLAYSURF.blit(resultSurf, resultRect)

    

    # global  
    # global ContinualSuccessFlag 

''' This is the loop of PyGame that actually drives the experiment.  I would like you to take note of the collosal list of global variables.
    This is probably really stupid practice, but again, we are looking at the legacy of my early work when I didn't really understand
    the proper way to build interaction between different objects.  It works, but it's unsightly, and I haven't had the nerve to even
    prune away some of the variables that serve no purpose in this particular paradigm.  It's harmless, but unaesthetic and sloppy.  I vow
    never build such lousy infrastructure again for the rest of my career as a technologist. -SP'''
#Main function
def main():
    pygame.init() #Pygame must be initiated
    
    
    
    '''These variables are variously set to global either because I declared them outside of Main and therefore
    must make them global to modify them, or I wanted to pass them to other functions more easily.
    this is all probably really stupid and if I knew how to do this right, I would.
    at least it works.  Variables will be explained as they crop up in the script.'''
    
    
    global DISPLAYSURF
    
    ##Font information
    global BASICFONT, BASICFONTSIZE
    global SCOREFONTSIZE, SCOREFONT
    
    global substage
    global maze
    global branch
    
    global DebugFlag
    global RecordBypass
    global stage
    global consolidatedoutput 
    global consolidatedhi 
    global consolidatedlo 
    global HiOutput
    global LoOutput
    global initialization

    global successflag
    global successtimer
    global successjar
    global Threshold
    global ContinualSuccessTimer
    global FirstSuccessTimer
    global TargetVal
    global countdown
    global OutputFilename
    global TS
    global BlocInterval
    global FixationInterval
    global NEXT

    global VoltMedian
    global VoltMax
    global VoltMin
    global VoltBaseline
    global consolidatedloNext
    global consolidatedhiNext
    global consolidatedoutputNext
    global Record
    global LeftTag
    global RightTag
    global resultarray 
    global Alphas
    global Alphamax
    global pausetime
    global alpha
    global Submit
    global Stampclock
    global stage
    
    
    global Stage1
    global Stage2
    global Stage3
    global Stage4
    global Stage4_1
    global Stage4_2    
    global Stage5
    global submitbutton
    


    resultarray = []    #this stores outputs from NFT rounds.  Successes and failures, as 1 and 0 respectively
    LeftTag = False     #This is the indication the direction the BCI expects the NFT command to go is left.
    RightTag = False    #I would hope I don't have to explain this, in light of the above explanation.  
    
    
    #This starts the 1st round when the recording starts.  by default it is false as by default there is no recording
    RecordBypass = False
    
    #stage switching happens at pause points, either from pressing "space", or hitting the "next" button on the console.
    stageswitch = False
    
    #dummy values.  but these variables govern recording of data
    recordtick = 0
    countdown = 0
    
    #dummy Alpha maximum Hz.  Determined in MainGui naturally, but sometimes it's useful to test things without actual EEG data
    Alphamax = 10
    
    #This fires the TMS at initialization.
    if FIRE_TMS_FLAG:
        tms = CCDLtms.TMS() #this calls a tms object from the CCDLtms library, courtesy of Darby
        tms.tms_arm()       #this actually fires the TMS
        
    #5 seconds are needed for the data stream to connect properly, in my experience.  this variable delays the beginning of the script
    initialization = time.time() + 5 
    
    #Initializing the font values
    BASICFONTSIZE = 20
    SCOREFONTSIZE = 40 
    BASICFONT = pygame.font.Font('freesansbold.ttf', BASICFONTSIZE) #basically Arial font at 20 pt
    SCOREFONT = pygame.font.Font('freesansbold.ttf', SCOREFONTSIZE)
    
    
    
    #These are dummy values for voltage based thresholds.
    VoltMax = 1001
    VoltMedian = 1000
    VoltMin = 999
    VoltBaseline = 1000
    VoltMedianArrayNext = []
    
 
    
    if FIRE_TMS_FLAG == True:
        tms.tms_fire(i=LOW_INTENSITY)
    
    # Flags for whether to quit or pause; starts paused.
    quittingtime = False 
    pausetime = True
    Disconnect = False
    LastDISCONNECT = False
    
    #This is used in counting success time; the "success time" counter goes forward only if this is true
    successflag = False
    
    #Initialize the pygame FPS clock
    FPSCLOCK = pygame.time.Clock()
    
    #Set the size of the screen and label it
    DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH,WINDOWHEIGHT)) 
    pygame.display.set_caption('NeuroFeedback')

    #Start with 0 points
    score = 0
    
    
    '''WHAT FOLLOWS IS THE INITIALIZATION OF VARIOUS IMAGES
    these are all used to display such features as the orb sprite, the maze structure, and '''
    
    #Creates the legend for the maze answer
    legend = pygame.sprite.Sprite()
    legend.image = pygame.image.load("images/legend.png").convert_alpha()

    submitbutton = pygame.image.load('images/submit.png').convert_alpha()  # loads the submit button for the mazes

    #ORB properties
    b = pygame.sprite.Sprite()          # define parameters of ORB sprite
    b.image = pygame.image.load("images/Orb.png").convert_alpha()
    '''Load the ORB sprite, confusingly still named "glider."  Let's just say the orb has a name, and that name is "Glider."
    Storytelling is an important element of our humanity.  Please try to be aware of best aspects of personhood. -SP'''
    b.rect = b.image.get_rect() # use image extent values
    b.rect.center = [WINDOWWIDTH/2, WINDOWHEIGHT/2] # put the orb in the center of the player window


    '''This is where the stage instructions are actually loaded as sprites from files.
        If there were to be any alterations in the number of instructions or their contents,
        this is where modifications would have to be made.  -SP'''
    Stage1 = pygame.sprite.Sprite() #initializes the image as a sprite
    Stage1.image = pygame.image.load("images/Stage1.png").convert_alpha() #this formats the image into something compatible with the surface
    Stage1.rect = Stage1.image.get_rect()   #this gets details about the instruction sprite, such as size
    Stage1.rect.center = [WINDOWWIDTH/2, WINDOWHEIGHT/2] #this puts the instructions in the center of the screen


    #each of the stages below is identical in terms of the code functions compared to Stage1 above
    Stage2 = pygame.sprite.Sprite()
    Stage2.image = pygame.image.load("images/Stage2.png").convert_alpha()
    Stage2.rect = Stage2.image.get_rect()
    Stage2.rect.center = [WINDOWWIDTH/2, WINDOWHEIGHT/2]

    Stage3 = pygame.sprite.Sprite()
    Stage3.image = pygame.image.load("images/Stage3.png").convert_alpha()
    Stage3.rect = Stage3.image.get_rect()
    Stage3.rect.center = [WINDOWWIDTH/2, WINDOWHEIGHT/2]

    Stage4 = pygame.sprite.Sprite()
    Stage4.image = pygame.image.load("images/Stage4.png").convert_alpha()
    Stage4.rect = Stage4.image.get_rect()
    Stage4.rect.center = [WINDOWWIDTH/2, WINDOWHEIGHT/2]

    Stage4_1 = pygame.sprite.Sprite()
    Stage4_1.image = pygame.image.load("images/Stage4_1.png").convert_alpha()
    Stage4_1.rect = Stage4.image.get_rect()
    Stage4_1.rect.center = [WINDOWWIDTH/2, WINDOWHEIGHT/2]

    Stage4_2 = pygame.sprite.Sprite()
    Stage4_2.image = pygame.image.load("images/Stage4_2.png").convert_alpha()
    Stage4_2.rect = Stage4.image.get_rect()
    Stage4_2.rect.center = [WINDOWWIDTH/2, WINDOWHEIGHT/2]


    Stage5 = pygame.sprite.Sprite()
    Stage5.image = pygame.image.load("images/Stage5.png").convert_alpha()
    Stage5.rect = Stage5.image.get_rect()
    Stage5.rect.center = [WINDOWWIDTH/2, WINDOWHEIGHT/2]


    '''Let the games (loop) begin!  Once this is initiated, which is nearly instantaneously after the main loop is initialized through the MainGui's righthand buttons, this
    will continue to cycle until the game is ended, pausing between stages.  At that point, the "next round" button is the means through which we go from one type of round to another.
    no surprises there, right?-SP'''
    while True:
        for event in pygame.event.get():    #Processes game events like quitting or keypresses
            if event.type == QUIT:
                pygame.quit()
                f.close()
                ts.close()
                con.close()
                quittingtime = True
                break

            '''This portion handles events such as button presses, pressing the 'x' to close the window, and mouse clicks.  The debug and control modes are legacy features. Expand or delete as you see fit.  Take note of the specifics of the stage conditionals: these relate to the maze rounds. -SP'''
            if event.type == pygame.MOUSEBUTTONDOWN:
                ## if mouse is pressed get position of cursor ##
                pos = pygame.mouse.get_pos()
                #this condition is for if a mouse click happens during the maze response period
                if ((stage == 5) or (stage == 6) or (stage == 7) or (stage == 8)) and branch == 3 and substage == 0:

                    '''#Each of these if conditionals is for one of the 8 answers, when selected by the user.
                    "believepath" is the path the user believes they have taken.  these conditionals make sure the right orb
                     is highlighted, and the correct information is stored.  -SP'''
                    if (WINDOWWIDTH / 2 - 730) < pos[0] < (WINDOWWIDTH / 2 - 670) and 170 < pos[1] < 230:   #the x and y of the mouse click must fall in the right areas
                        believepath = [0,0,0]   #believepath is the path the subject believes they have taken
                        print '1 has been selected (', believepath, ')'

                    if (WINDOWWIDTH / 2 - 530) < pos[0] < (WINDOWWIDTH / 2 - 470) and 170 < pos[1] < 230:
                        believepath = [0,0,1]
                        print '2 has been selected (', believepath, ')'

                    if (WINDOWWIDTH / 2 - 330) < pos[0] < (WINDOWWIDTH / 2 - 270) and 170 < pos[1] < 230:
                        believepath = [0,1,0]
                        print '3 has been selected (', believepath, ')'

                    if (WINDOWWIDTH / 2 - 130) < pos[0] < (WINDOWWIDTH / 2 - 70) and 170 < pos[1] < 230:
                        believepath = [0,1,1]
                        print '4 has been selected (', believepath, ')'

                    if (WINDOWWIDTH / 2 + 70) < pos[0] < (WINDOWWIDTH / 2 + 130) and 170 < pos[1] < 230:
                        believepath = [1,0,0]
                        print '5 has been selected (', believepath, ')'

                    if (WINDOWWIDTH / 2 + 270) < pos[0] < (WINDOWWIDTH / 2 + 330) and 170 < pos[1] < 230:
                        believepath = [1,0,1]
                        print '6 has been selected (', believepath, ')'

                    if (WINDOWWIDTH / 2 + 470) < pos[0] < (WINDOWWIDTH / 2 + 530) and 170 < pos[1] < 230:
                        believepath = [1,1,0]
                        print '7 has been selected (', believepath, ')'

                    if (WINDOWWIDTH / 2 + 670) < pos[0] < (WINDOWWIDTH / 2 + 730) and 170 < pos[1] < 230:
                        believepath = [1,1,1]
                        print '8 has been selected (', believepath, ')'


                '''#This mouseclick is for when "submit" is clicked.  That is what "branch 3" is: the mouse selection point.    '''
                if ((stage == 5) or (stage == 6) or (stage == 7) or (stage == 8)) and branch == 3:
                    if SubmitButton.collidepoint(pos) and len(believepath) == 3:
                        substage = substage + 1 #we move forward a substage in that case

            #THESE ARE FOR KEYPRESS EVENTS
            if event.type == pygame.KEYDOWN:  #press space to terminate pauses between blocs
                if event.key == pygame.K_d:   #d makes the debug flag toggle.  this is for displaying info.
                    DebugFlag = not DebugFlag
                #if event.key == pygame.K_SPACE: #space bar, when pushed during a pause, repeats the last round. purely debug, so I've disabled it for now.
                    #if pausetime == True:
                        #NEXT = True
                        #stage = stage - 1


                if event.key == pygame.K_p:  #pressing p in the beginning makes the baseline very short
                    if stage == 0:
                        BlocInterval = 100000    #arbitrarily high
                        FixationInterval = 2     #means only 2 seconds of waiting for the baseline to finish
                        print('Debug values enabled')


        '''This checks SPTruVal, which it should be receiving from the Visualizer script.
           SPTruVal is the Mu input from the datastream.  So, it's only received when Alpha is false. -SP'''
        if alpha == False:
            TargetVal = SPTruVal    #by default the visualizer script feeds us the Mu values, which is what we do if we do not do Alpha

        #this sets the variables in place for the next stage, every stage except the initial one.
        if NEXT == True and stage != 0:
                    if pausetime == True:   #we must be at a pause, which is also the default starting state of the NFT window
                        pausetime = False   #we are no longer paused
                        NEXT = False        #we must make sure that we are no longer in a state of looking for the next round
                        RecordBypass = False #Likely unnecessary, but I'm playing it safe for now. this should only affect the 1st round transition
                        countdown = time.time() + BlocInterval #This is the number of seconds in a Glider game block; it is set arbitrarily high for the non-baselining rounds. #FIXIT

                        '''All these values must be reset at the beginning of a stage if we are going to get new outputs
                           and baselines. -SP'''
                        score = 0
                        successjar = 0
                        recordtick = time.time()+.25   #Collecting values at a 250 ms interval; decrease to up sampling rate
                        consolidatedoutput = []
                        consolidatedhi = []
                        consolidatedlo = []
                        consolidatedoutputNext = []
                        consolidatedhiNext = []
                        consolidatedloNext = []
                        VoltMedianArrayNext = []
                        resultarray = []
                        trials = []
                        believepath = []
                        brainpath = []
                        Submit = False

                        #start off with a buffer before the first stim
                        substagecountdown = time.time() + 5
                        print 'substagecountdown is set to ', int(substagecountdown)
                        print 'branch ', branch, ' substage, ', substage, ' maze ', maze#, ' countdown ', substagecountdown-time.time()

                        if stage == 1 or stage == 2:
                            b.rect.center = [WINDOWWIDTH/2, WINDOWHEIGHT/2]
                        #This is for the baselining stages at the beginning and end
                        if stage == 0: #or stage == 5:
                            countdown = time.time() + FixationInterval #Number of seconds for Baseline block
                        else:
                            LeftRightTimer = time.time() + 5
                            LeftFlag = True
                            LRPauseFlag = True

                        #These steps manage the additional instructions between stages 4 and 5.
                        if stage  == 4:
                            stage = 4.1
                        elif stage == 4.1:
                            stage = 4.2
                        elif stage == 4.2:
                            print 'Next stage is the maze'
                            stage = 5
                        else:
                            stage = stage + 1
                            print 'stage is increased by 1 here'


        '''This portion accounts for the possibility of recording bypass, which is what happens in the first baseline.
        This really should be unified with the above function in some way, but I never managed to get around to it.
        Oh well, at least it does what it's supposed to.  I won't repeat that mistake next time I build something like this.
        ... I've said that a lot, haven't I?
        Also, this portion is where the output file is created.  Note that the maze answers are printed into the file
        from the getgo. -SP'''
        if stage == 0 and RecordBypass == True:
            if pausetime == True: #Inelegant; make a module for this later so as to encompass keypresses
                if stage == 0:
                    print('outputfilename is ' + OutputFilename)
                    f = open(OutputFilename, 'w') #This should have the custom name plugged in later;
                    ts = open(TS, 'w')
                    f.write('Maze Answers: ,')
                    for i in numbers:
                        f.write(str(i) + ',')
                    f.write('\n')
                    f.close()
                    f = open(OutputFilename, 'a')


                pausetime = False
                RecordBypass = False # Can't have the recordbypass triggering prematurely for the second recording.



                countdown = time.time() + BlocInterval #This is the number of seconds in a Glider game block; set to 300 when done debugging

                score = 0
                recordtick = time.time() + 0.25   #Collecting values at a 250 ms interval; decrease to up sampling rate
                consolidatedoutput = []
                consolidatedhi = []
                consolidatedlo = []
                consolidatedoutputNext = []
                consolidatedhiNext = []
                consolidatedloNext = []
                VoltMedianArray = []


                                #This is for the baselining stages at the beginning and end
                if stage == 0:
                    Record = True
                    Stampclock = time.time()

                    countdown = time.time() + FixationInterval #Number of seconds for Baseline block
                '''This governs the peculiarities of the sub-stages responsible for displaying instructions. '''
                if stage  == 4:
                    stage = 4.1
                elif stage == 4.1:
                    stage = 4.2
                elif stage == 4.2:
                    print 'Next stage is the maze'
                    stage = 5
                else:
                    stage = stage + 1
                    print 'stage is increased by 1 here'


        '''needed to exit the program gracefully.  Breaking the loop is necessary to terminate things without leaving an unkillable zombie window.'''
        if quittingtime == True:
                break





        '''If the game is at a pausing point, such as the beginning screen.  Refer to the pausepoint function before the main function for more details.'''
        if pausetime == True:
            Pausepoint(stage, score)
            pygame.display.update()
            FPSCLOCK.tick(FPS)
            continue

        if stage == 4.1 or stage == 4.2:
            pausetime = True
            print 'next page?'
            continue







        NEXT = False #This prevents a multi-pressing problem
        '''Every quarter of a second, the voltage and spectral values are recorded for a control file.  this is a legacy function that could be used again for controls, though in the
        context of the BIAV, it makes no sense to have controls.  It's hard enough to get people to perform the task correctly when training them under optimal conditions.  However,
        this code also helps establish baselines, but in a rather convoluted way.  note the outputs that are being appended to here.  they are used to calculate the new baseline at the
        end of the first round. -SP'''
        if time.time() >= recordtick:
            recordtick = time.time()+.25  #This collects data every 250 ms.  Lower this number for higher resolution
            if stage == 1 or (VoltBaseline < VoltMin + 400 and VoltBaseline > VoltMax - 400 and HighNoiseFlag == False and LowNoiseFlag == False):
                #print('Voltmin', VoltMin, 'Voltmax', VoltMax, 'VoltBaseline', VoltBaseline)
                consolidatedoutputNext.append(TargetVal)

                consolidatedhiNext.append(HiNoise)
                consolidatedloNext.append(LoNoise)
                VoltMedianArrayNext.append(VoltMedian)
                #print len(consolidatedoutputNext)



        '''If the countdown timer reaches zero (in other words, if the duration of a timed stage is completed), which at this point
           means only the resting state -SP'''
        if time.time() > countdown:
            #Record = False

            #if stage == 2 or stage == 3 or stage == 4 or stage == 5:
            '''I'm going to level with you.  I may have had a good reason for retaining the old array of output values, but I'm pretty sure
            it serves no purpose in this script.  I'm just terrified that somewhere there is some weird case where these variables are called,
            even if they aren't used in any meaningful way, so I never got to removing them.  You should probably just ignore these.  -SP'''
            consolidatedoutput = consolidatedoutputNext
            consolidatedhi = consolidatedhiNext
            consolidatedlo = consolidatedloNext
            VoltMedianArray = VoltMedianArrayNext


            '''What follows is a series of print statements that tell the administrator about previous sessions.
			These values are also written to a text file for future examination.  This is very similar to what is in the NFT script. -SP'''
            print("STAGE " + str(stage)) #Just printing the stage

            output = sum(consolidatedoutput)/len(consolidatedoutput)
            f.write(str(output) + ',')
            if alpha == True and stage == 1:
                    print 'after alpha'
                    #print Alphas
                    Alphas = np.mean(Alphas, axis=0) #from mean
                    #Alphas = np.median(Alphas, axis=0)#From Median

                    print 'median ', np.median(Alphas, axis=0), ' mean is ', np.mean(Alphas, axis=0)
                    #print 'probalo?'
                    AlphasTrue = Alphas[2:-2]
                    print 'alphas are ', Alphas
                    Alphamax = np.argmax(AlphasTrue)
                    Alphamax = Alphamax + 2
                    print 'Alpha max index is ', Alphamax, ' and alpha range is ', Alphamax-2, ' ', Alphamax+3
                    AlphaDensity = np.mean(Alphas[Alphamax-2:Alphamax+3]) #the range is -2 from the true value to +2 from the true value
                    Alphamax = Alphamax + 6


                    print "alpha maximum is ", str(Alphamax), ' Hz'
                    f.write('\nmax alpha:,' + str(Alphamax) + '\n')


                    print 'Alphas are ', Alphamax-2, ' to ', Alphamax+2

                    #print 'Alpha powers are ',
                    #print 'true Alpha density is ', AlphaDensity
                    output = AlphaDensity
                    f.write('Alpha Power Mean:,' + str(AlphaDensity) + ',' )
                    print 'Alpha Power: ', AlphaDensity
                    Threshold = AlphaDensity
            elif alpha == True:
                output = AlphaDensity
                Threshold = AlphaDensity



            ''' If Alpha is false, then we are simply using the 'output', which is keyed to the mu spectral values.'''
            if alpha == False:
                Threshold = output
            print("Data Baseline is: " + str(output))


            deviance = np.std(consolidatedoutput)
            f.write('STD: ,' + str(deviance) + ',')
            print("Data baseline STDEV:" + str(deviance))

            HiOutput = sum(consolidatedhi)/len(consolidatedhi)
            f.write('\nHigh Noise Mean and STD: ,' + str(HiOutput) + ',')
            print("High Freq. Noise Baseline: " + str(HiOutput))


            HiDev = np.std(consolidatedhi)
            f.write(str(HiDev) + '\n')
            print("High Freq. Noise STDEV: " + str(HiDev))

            LoOutput = sum(consolidatedlo)/len(consolidatedlo)
            f.write('Low Noise Mean and STD: ,' + str(LoOutput) + ',')
            print("Low Freq. Noise Baseline is: " + str(LoOutput))

            LoDev = np.std(consolidatedlo)
            f.write(str(LoDev) + ',\n')
            print("Low Freq. Noise STDev is: " + str(LoDev))

            pausetime = True



            f.write('\n') #New line
            f.close()
            f = open(OutputFilename, 'a')
            b.rect.y = WINDOWHEIGHT/2




            #This is for the voltage values
            VoltBaseline = np.mean(VoltMedianArray)
            print(str(round(np.mean(VoltMedianArray), 2))+' v is the average of the Median Voltages.') #falseflag

            continue




        #baselining at stages 1 and 6
        if stage == 1: #or stage == 6:
            fixation(recordtick)
            pygame.display.update()

            FPSCLOCK.tick(FPS)
            continue


        #Final exit after last stage
        if stage == 9:
            pygame.quit()
            f.close()
            ts.close()
            print("Game over, man.  Game over.")
            quittingtime = True
            break

        '''Clear the stage every frame so nothing lingers that should not be there.'''
        DISPLAYSURF.fill(GREY)

        '''ALPHA MAGIC, BABY! sets the Target Value to Alpha, if Alpha is what we are looking at.
        Note that it is keyed to the individual alpha as per the alpha max calculations done in the MainGui.'''
        if alpha == True:
            TargetVal = np.mean(densityA[Alphamax-2:Alphamax+3])





        reticle(TEXTCOLOR)

        '''This displays the timeseries in the case of you wanting to look at debug values.
            it was useful in making sure I was reading from the channels I meant to be.  hopefully,
            you will not need to use it for that purpose, though if you change the target channels,
            you will want to do this. It's the best way to be sure you are measuring what you think you are. -SP'''
        if DebugFlag == True:

            EEGTimeSeries = SMRTimeSeries
            mean = np.mean(EEGTimeSeries)
            EEGTimeSeries = EEGTimeSeries - mean
            timeseriesindex = 0        #This is each individual point in the series.
            numpairs = []
            for x in EEGTimeSeries:
                timeseriesindex = timeseriesindex + 1 #We go through each point.
                numpairs.append([500+timeseriesindex,x*.75+725])
            pygame.draw.lines(DISPLAYSURF,CYAN,False,numpairs,1)


            EEGTimeSeries = SMRTimeSeries2
            mean = np.mean(EEGTimeSeries)
            EEGTimeSeries = EEGTimeSeries - mean
            timeseriesindex = 0        #This is each individual point in the series.
            numpairs = []
            for x in EEGTimeSeries:
                timeseriesindex = timeseriesindex + 1 #We go through each point.
                numpairs.append([500+timeseriesindex,x*0.75+825])
            pygame.draw.lines(DISPLAYSURF,YELLOW,False,numpairs,1)

            EEGTimeSeries = AlphaSeries
            mean = np.mean(EEGTimeSeries)
            EEGTimeSeries = EEGTimeSeries - mean
            timeseriesindex = 0        #This is each individual point in the series.
            numpairs = []
            for x in EEGTimeSeries:
                timeseriesindex = timeseriesindex + 1 #We go through each point.
                numpairs.append([500+timeseriesindex,x*0.75+925])
            pygame.draw.lines(DISPLAYSURF,WHITE,False,numpairs,1)

            if alpha == False:
                EEGTimeSeries = SMRDens
                timeseriesindex = 0        #This is each individual point in the series.
                numpairs = []
                for x in EEGTimeSeries:
                    timeseriesindex = timeseriesindex + 1 #We go through each point.
                    yval = 925-(x)*3
                    if yval < 700:
                        yval = 700
                    numpairs.append([1100+timeseriesindex*50,yval])
                pygame.draw.lines(DISPLAYSURF,CYAN,False,numpairs,1)


                EEGTimeSeries = SMRDens2
                timeseriesindex = 0        #This is each individual point in the series.
                numpairs = []
                for x in EEGTimeSeries:
                    timeseriesindex = timeseriesindex + 1 #We go through each point.
                    yval = 925-(x)*3
                    if yval < 700:
                        yval = 700
                    numpairs.append([1100+timeseriesindex*50,yval])
                pygame.draw.lines(DISPLAYSURF,YELLOW,False,numpairs,1)

            if alpha == True:
                EEGTimeSeries = densityA[Alphamax-2:Alphamax+3]
                timeseriesindex = 0        #This is each individual point in the series.
                numpairs = []
                for x in EEGTimeSeries:
                    timeseriesindex = timeseriesindex + 1 #We go through each point.
                    yval = 925-(x)*3
                    if yval < 700:
                        yval = 700
                    numpairs.append([100+timeseriesindex*50,yval])
                pygame.draw.lines(DISPLAYSURF,WHITE,False,numpairs,1)

                EEGTimeSeries = densityA[Alphamax-2:Alphamax+3]
                timeseriesindex = 0        #This is each individual point in the series.
                numpairs = []
                for x in EEGTimeSeries:
                    timeseriesindex = timeseriesindex + 1 #We go through each point.
                    yval = 925-(Threshold)*3
                    if yval < 700:
                        yval = 700
                    numpairs.append([100+timeseriesindex*50,yval])
                pygame.draw.lines(DISPLAYSURF,RED,False,numpairs,1)

                EEGTimeSeries = densityA[Alphamax-2:Alphamax+3]
                timeseriesindex = 0        #This is each individual point in the series.
                numpairs = []
                for x in EEGTimeSeries:
                    timeseriesindex = timeseriesindex + 1 #We go through each point.
                    yval = 925-(np.mean(densityA[Alphamax-2:Alphamax+3]))*3
                    if yval < 700:
                        yval = 700
                    numpairs.append([100+timeseriesindex*50,yval])
                pygame.draw.lines(DISPLAYSURF,CYAN,False,numpairs,1)




        '''This moves the ball, whether it is visible or not, during BCI periods.  This is identical to what the NFT script does.
        Stage 1 is a baselining stage. -SP'''

        if stage > 1:
            if TargetVal < Threshold :   #This is a success state.
                b.rect.x	=  b.rect.x + 3                 #It is counterintuitive, but lower numbers means higher on the screen.
                b.image = pygame.image.load("images/orb.png").convert_alpha()
                #successflag = True
            else: #The only other possibility is that there are no noise flags, but the signal band isn't high enough to pass threshold. This is the second of 2 failure states.
                b.image = pygame.image.load("images/orb.png").convert_alpha()
                b.rect.x = b.rect.x - 3

        '''This is for the NFT rounds 2 and 3.  Note that for NFT round 2, we are doing some active baselining like with the NFT script.
           This is to make sure that the baseline is as close to being in the middle of a subject's "high" and "low" states as possible.
            Also, if the time is wrong for that ball to move, whether it is visible or not, we want to make sure that it doesn't keep moving.
            From here on out, we see that this is the portion of the code that governs the stages within the NFT: is it time for the stimulation?
            is it time for the blue cross, response time?  is it somewhere in between?
            This chunk of code is what governs that process.  -SP '''
        if stage == 2 or stage == 3:
            if LeftRightTimer < time.time():
                if LRPauseFlag == True:
                    print 'pause is over'
                    LeftFlag = not LeftFlag
                    LRPauseFlag = False
                    if LeftFlag == True:
                        LeftTag = True
                    else:
                        RightTag = True
                    LeftRightTimer = time.time() + leftrightperiod  #Remember this?  here we see the left-right evaluation period begins.  This is how long the cross is blue.
                else:
                    print 'pause'
                    ts.write('feedback received,' + str(time.time()-Stampclock) + '\n')
                    #Record = False
                    LRPauseFlag = True
                    LeftRightTimer = time.time() + poststimperiod
                    if LeftFlag == True:
                        if b.rect.centerx < WINDOWWIDTH/2:
                            score = score + 1
                            coin.play()
                            resultarray.append(1)

                        else:
                            if stage == 2:
                                Threshold = Threshold - 0.5*(30-len(resultarray))/30
                                print 'Threshold is now lower: ', Threshold
                            resultarray.append(0)

                    if LeftFlag == False:
                        if b.rect.centerx > WINDOWWIDTH/2:
                            score = score + 1
                            coin.play()
                            resultarray.append(1)

                        else:
                            if stage == 2:
                                Threshold = Threshold + 0.5*(30-len(resultarray))/30
                                print 'Threshold is now higher: ', Threshold
                            resultarray.append(0)

                    percent = np.mean(resultarray)
                    print(resultarray)
                    print '%s TOTAL PERCENT', (percent), ' of ', len(resultarray)
            else:
                if LRPauseFlag == True:
                    b.rect.center = [WINDOWWIDTH/2, WINDOWHEIGHT/2]
                    resultSurf = SCOREFONT.render('Wait', True, TEXTCOLOR)
                    if stage == 3 or stage == 4:
                        resultSurf = SCOREFONT.render('Wait', True, TEXTCOLOR)
                    resultRect = resultSurf.get_rect()
                    resultRect.center = (WINDOWWIDTH/2 - 15, 400)
                    DISPLAYSURF.blit(resultSurf, resultRect)


                else:
                    reticle(BLUE)  #Remember, blue means go.

                    if LeftFlag == False:
                        resultSurf = SCOREFONT.render('Right  ', True, TEXTCOLOR)
                        if alpha == True:
                            resultSurf = SCOREFONT.render('Right (Focus)', True, TEXTCOLOR)
                        resultRect = resultSurf.get_rect()
                        resultRect.center = (WINDOWWIDTH/2, 400)
                        DISPLAYSURF.blit(resultSurf, resultRect)
                    else:
                        resultSurf = SCOREFONT.render('Left  ', True, TEXTCOLOR)
                        if alpha == True:
                            resultSurf = SCOREFONT.render('Left (Relax)', True, TEXTCOLOR)
                        resultRect = resultSurf.get_rect()
                        resultRect.center = (WINDOWWIDTH/2, 400)
                        DISPLAYSURF.blit(resultSurf, resultRect)



        '''The disappearing act of the ball is automatically governed by the script.
           It happens at stage 2, and it never returns.'''
        if stage > 2:
            b.rect.y = 10000     #DEBUGFIX

        '''This collates the subject responses during the NFT rounds.'''
        if (stage == 2 or stage == 3) and len(resultarray) == 4:
            ts.write('stage end ' + str(stage) + ','  + str(time.time()-Stampclock) + '\n')
            f.write('Stage ' + str(stage) + ' subject responses: ,')
            for i in resultarray:
                f.write( str(i) + ',')
            f.write('\n')
            resultarray = []
            pausetime = True



        if (stage == 4) and len(resultarray) == 4:
            ts.write('stage end ' + str(stage) + ','  + str(time.time()-Stampclock) + '\n')
            f.write('Stage ' + str(stage) + ' subject responses: ,')
            for i in resultarray:
                f.write( str(i) + ',')
            f.write('\n')
            resultarray = []
            pausetime = True

        if stage == 4:
            if LeftRightTimer < time.time():
                if LRPauseFlag == True:
                    print 'pause is over'
                    LeftFlag = not stimarray[len(resultarray)] #1 is right, 0 is left
                    LRPauseFlag = False
                    print 'unpause'
                    if LeftFlag == True:
                        LeftTag = True
                    else:
                        RightTag = True
                    LeftRightTimer = time.time() + leftrightperiod + leftrightbuffer  #FIXTHIS
                    if stimarray[len(resultarray)] == 1:
                        print 'big stim'
                        ts.write('big stim,' + str(time.time()-Stampclock)  + '\n')
                        if FIRE_TMS_FLAG == True:
                            tms.tms_fire(i=HIGH_INTENSITY)
                    else:
                        print 'small stim'
                        ts.write('small stim,' + str(time.time()-Stampclock)  + '\n')
                        if FIRE_TMS_FLAG == True:
                            tms.tms_fire(i=LOW_INTENSITY)
                else:
                    print 'pause'
                    #Record = False
                    LRPauseFlag = True
                    LeftRightTimer = time.time() + poststimperiod  #FIXTHIS
                    if LeftFlag == True:
                        if b.rect.centerx < WINDOWWIDTH/2:
                            score = score + 1
                            coin.play()
                            resultarray.append(1)

                        else:
                            resultarray.append(0)

                    if LeftFlag == False:
                        if b.rect.centerx > WINDOWWIDTH/2:
                            score = score + 1
                            coin.play()
                            resultarray.append(1)

                        else:
                            resultarray.append(0)

                    percent = np.mean(resultarray)
                    print(resultarray)
                    print '%s TOTAL PERCENT', (percent), ' of ', len(resultarray)
            else:
                if LRPauseFlag == True:
                    b.rect.centerx = WINDOWWIDTH/2
                    #resultSurf = SCOREFONT.render('WAIT FOR STIMULATION.', True, TEXTCOLOR)
                    resultRect = resultSurf.get_rect()
                    resultRect.center = (WINDOWWIDTH/2 - 15, 400)
                    #DISPLAYSURF.blit(resultSurf, resultRect)
                    if time.time() + 1 > LeftRightTimer:
                            reticle(RED)
                else:
                    if time.time() + 15 > LeftRightTimer:

                        #resultSurf = SCOREFONT.render('RESPOND.', True, TEXTCOLOR)
                        reticle(BLUE)


                    else:
                        b.rect.centerx = WINDOWWIDTH/2
                        resultRect = resultSurf.get_rect()
                        resultRect.center = (WINDOWWIDTH/2 - 15, 400)


        if (stage == 5) or (stage == 6) or (stage == 7) or (stage == 8):

            if numbers[maze] == 1:
                truepath = [0,0,0]
            if numbers[maze] == 2:
                truepath = [0,0,1]
            if numbers[maze] == 3:
                truepath = [0,1,0]
            if numbers[maze] == 4:
                truepath = [0,1,1]
            if numbers[maze] == 5:
                truepath = [1,0,0]
            if numbers[maze] == 6:
                truepath = [1,0,1]
            if numbers[maze] == 7:
                truepath = [1,1,0]
            if numbers[maze] == 8:
                truepath = [1,1,1]


            if not branch == 3:
                if time.time() > substagecountdown:
                    print 'branch ', branch, ' substage, ', substage, ' maze ', maze #' countdown ', substagecountdown-time.time()
                    if substage == 0: #stim now. begin 5 sec wait

                        if truepath[branch] == 1:
                            print 'big stim'
                            if FIRE_TMS_FLAG == True:
                                tms.tms_fire(i=HIGH_INTENSITY)
                            ts.write('big stim,' + str(time.time()-Stampclock) + '\n')
                        else:
                            print 'small stim'
                            ts.write('small stim,' + str(time.time()-Stampclock) + '\n')
                            if FIRE_TMS_FLAG == True:
                                tms.tms_fire(i=LOW_INTENSITY)
                            #smallstim
                        substage = substage + 1
                        substagecountdown = time.time() + mazebuffer #5

                    elif substage == 1: #Get Answer
                        print 'get answer'
                        b.rect.centerx = WINDOWWIDTH/2
                        substagecountdown = time.time() + answerperiod
                        substage = substage + 1


                    elif substage == 2: #Evaluate Answer
                        substagecountdown = time.time() + answerperiod + 3
                        if b.rect.centerx  < WINDOWWIDTH/2:
                            brainpath.append(0)
                        else:
                            brainpath.append(1)
                        print 'brainpath is ', brainpath
                        branch = branch + 1
                        substage = 0
                        substagecountdown = time.time() + leftrightbuffer
                        print 'maze is ', numbers[maze], ' and truepath is ', truepath
                else:
                    if substage == 0:
                        if time.time() + 5 > substagecountdown:
                            resultRect = resultSurf.get_rect()
                            resultRect.center = (WINDOWWIDTH/2, 400)
                        #disp "wait for stim"
                        if time.time() + 1 > substagecountdown:
                            reticle(RED)
                        #make red cross if less than 1 second
                    if substage == 1:
                        if time.time() + 3 > substagecountdown:
                            resultRect = resultSurf.get_rect()
                            resultRect.center = (WINDOWWIDTH/2, 400)
                            b.rect.centerx = WINDOWWIDTH/2

                    if substage == 2:
                        reticle(BLUE)


                        resultRect = resultSurf.get_rect()
                        resultRect.center = (WINDOWWIDTH/2, 400)
                    else:
                        b.rect.centerx = WINDOWWIDTH/2



            else:
                b.rect.centerx = WINDOWWIDTH/2
                reticle(GREY)
                if substage == 0 or substage == 1:
                    #ResetButton = DISPLAYSURF.blit(resetbutton, (200, 800))

                    if substage == 0:
                        SubmitButton = DISPLAYSURF.blit(submitbutton, (1400, 800))

                    for i in range(0, 2):
                        pygame.draw.line(DISPLAYSURF, TEXTCOLOR, (WINDOWWIDTH/2, 800), ((WINDOWWIDTH/2 - 400 + 800*i), 600), 4)

                    for i in range(0, 4):
                        if i < 2:
                            pygame.draw.line(DISPLAYSURF, TEXTCOLOR, (WINDOWWIDTH / 2 - 400, 600), ((WINDOWWIDTH/2 - 600 + 400*i), 400), 4)
                        else:
                            pygame.draw.line(DISPLAYSURF, TEXTCOLOR, (WINDOWWIDTH / 2 + 400, 600), ((WINDOWWIDTH / 2 + 200 + 400*(i-2)), 400), 4)


                    for i in range(0, 8):
                        if i < 2:
                            pygame.draw.line(DISPLAYSURF, TEXTCOLOR, (WINDOWWIDTH / 2 - 600, 400), ((WINDOWWIDTH/2 - 700 + 200*i), 200), 4)
                        elif i < 4:
                            pygame.draw.line(DISPLAYSURF, TEXTCOLOR, (WINDOWWIDTH / 2 - 200, 400), ((WINDOWWIDTH/2 - 700 + 200*i), 200), 4)
                        elif i < 6:
                            pygame.draw.line(DISPLAYSURF, TEXTCOLOR, (WINDOWWIDTH / 2 + 200, 400), ((WINDOWWIDTH/2 - 700 + 200*i), 200), 4)
                        else:
                            pygame.draw.line(DISPLAYSURF, TEXTCOLOR, (WINDOWWIDTH / 2 + 600, 400), ((WINDOWWIDTH/2 - 700 + 200*i), 200), 4)


                    if substage == 1:
                        #SubmitButton = DISPLAYSURF.blit(submitbutton, (1400, 800))
                        legend.image = pygame.image.load("images/legend.png").convert_alpha()
                        legend.rect = legend.image.get_rect()
                        legend.rect.center = [1300, WINDOWHEIGHT/2 + 400]
                        DISPLAYSURF.blit(legend.image, legend.rect)
                        if substage == 1 and Submit == True:
                            Submit = False
                            substage = substage + 1
                        
                        
                        #brainpath
                        
                        pygame.draw.line(DISPLAYSURF, ORANGE, (WINDOWWIDTH/2, 800), ((WINDOWWIDTH/2 - 400 + 800*brainpath[0]), 600), 9)
            
                        
                        
                        if brainpath[0] == 0:
                            pygame.draw.line(DISPLAYSURF, ORANGE, (WINDOWWIDTH / 2 - 400, 600), ((WINDOWWIDTH/2 - 600 + 400*brainpath[1]), 400), 9)
                        if brainpath[0] == 1:
                            pygame.draw.line(DISPLAYSURF, ORANGE, (WINDOWWIDTH / 2 + 400, 600), ((WINDOWWIDTH / 2 + 200 + 400*(brainpath[1])), 400), 9)
            
                        for i in range(0, 8):
                            if brainpath[0] == 0 and brainpath[1] == 0:
                                pygame.draw.line(DISPLAYSURF, ORANGE, (WINDOWWIDTH / 2 - 600, 400), ((WINDOWWIDTH/2 - 700 + 200*brainpath[2]), 200), 9)
                            elif brainpath[0] == 0 and brainpath[1] == 1:
                                pygame.draw.line(DISPLAYSURF, ORANGE, (WINDOWWIDTH / 2 - 200, 400), ((WINDOWWIDTH/2 - 700 + 200*(brainpath[2]+2)), 200), 9)
                            elif brainpath[0] == 1 and brainpath[1] == 0:
                                pygame.draw.line(DISPLAYSURF, ORANGE, (WINDOWWIDTH / 2 + 200, 400), ((WINDOWWIDTH/2 - 700 + 200*(brainpath[2]+4)), 200), 9)
                            else:
                                pygame.draw.line(DISPLAYSURF, ORANGE, (WINDOWWIDTH / 2 + 600, 400), ((WINDOWWIDTH/2 - 700 + 200*(brainpath[2]+6)), 200), 9)          

                        

                            

                    pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2, 800], 25)  
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 - 400, 600], 25)  
                    if len(believepath) > 0:
                        if believepath[0] == 0:
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 - 400, 600], 25)    
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 + 400, 600], 25)  
                    if len(believepath) > 0:
                        if believepath[0] == 1:
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 + 400, 600], 25)  

                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 - 600, 400], 25)  
                    if len(believepath) > 1:
                        if believepath[0] == 0 and believepath[1] == 0:
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 - 600, 400], 25)  
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 - 200, 400], 25)  
                    if len(believepath) > 1:
                        if believepath[0] == 0 and believepath[1] == 1:                            
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 - 200, 400], 25)  
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 + 200, 400], 25)  
                    if len(believepath) > 1:
                        if believepath[0] == 1 and believepath[1] == 0:                            
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 + 200, 400], 25)  
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 + 600, 400], 25)  
                    if len(believepath) > 1:
                        if believepath[0] == 1 and believepath[1] == 1:
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 + 600, 400], 25)  
                    
                    

                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 - 700, 200], 25)  
                    if len(believepath) > 2:
                        if believepath[0] == 0 and believepath[1] == 0 and believepath[2] == 0:                                 
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 - 700, 200], 25)  
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 - 500, 200], 25)  
                    if len(believepath) > 2:
                        if believepath[0] == 0 and believepath[1] == 0 and believepath[2] == 1:                                 
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 - 500, 200], 25)  
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 - 300, 200], 25)  
                    if len(believepath) > 2:
                        if believepath[0] == 0 and believepath[1] == 1 and believepath[2] == 0:                                 
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 - 300, 200], 25)  
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 - 100, 200],  25)  
                    if len(believepath) > 2:
                        if believepath[0] == 0 and believepath[1] == 1 and believepath[2] == 1:                                 
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 - 100, 200],  25)  

                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 + 100, 200],  25)  
                    if len(believepath) > 2:
                        if believepath[0] == 1 and believepath[1] == 0 and believepath[2] == 0:                                 
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 + 100, 200],  25)  
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 + 300, 200], 25)  
                    if len(believepath) > 2:
                        if believepath[0] == 1 and believepath[1] == 0 and believepath[2] == 1:     
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 + 300, 200], 25)  
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 + 500, 200], 25)                              
                    if len(believepath) > 2:
                        if believepath[0] == 1 and believepath[1] == 1 and believepath[2] == 0:                                 
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 + 500, 200], 25)                              
                    
                    pygame.draw.circle(DISPLAYSURF, TEXTCOLOR, [WINDOWWIDTH / 2 + 700, 200], 25)  
                    if len(believepath) > 2:
                        if believepath[0] == 1 and believepath[1] == 1 and believepath[2] == 1:                                 
                            pygame.draw.circle(DISPLAYSURF, BLUE, [WINDOWWIDTH / 2 + 700, 200], 25)  

                    if substage == 1:            
                        truepos = truepath[0]*4 + truepath[1]*2 + truepath[2] 
                        pygame.draw.circle(DISPLAYSURF, YELLOW, [WINDOWWIDTH / 2 - 700 + truepos*200 , 200], 25) 
                            

                    
                            
                if substage == 2:
                    maze = maze + 1
                    substagecountdown = time.time() + postmazebuffer #8   
                    f.write('Real Maze '+ str(maze) + ': ,')
                    for i in truepath:
                        f.write(str(i) + ',')
                    f.write('NFT Answers: ,')                        
                    for i in brainpath:
                        f.write(str(i) + ',')
                    f.write('Intended Answers: ,')                        
                    for i in believepath:
                        f.write(str(i) + ',')
                    f.write('\n')
                    branch = 0
                    brainpath = []
                    believepath = []
                    substage = 0
                    
                    if maze == 32:
                        quittingtime = True
                        f.close()
                        ts.close()
                        print 'itza a wrap!'
                        break
                    
                    if maze%8 == 0:  #if there is no remainder when dividing the current maze number by 8
                        pausetime = True
   
   
        
        #Displays debug information, if debug mode is true.  hit 'd' to do this
        if DebugFlag == True:
            displayDEBUG(round(TargetVal,3))
        
        
  
        Submit = False
        
        #Final draws and screen update
        drawSprite(b) #Draws the glider in his new position
        pygame.display.flip() #needed to draw the >< ~STARS~ ><
        pygame.display.update() #Refresh all the details that do not fall under the "flip" method. SP NOTE: I don't understand the difference very well.
        
        FPSCLOCK.tick(FPS) #Tells the game system that it is not untouched by the inexorable march of time

if __name__=='__main__':
    main()
	
