import cv2 as cv
import numpy as np
import math
import pyttsx3


def main():
    vid = cv.VideoCapture(2)
    engine = pyttsx3.init()
    engine.runAndWait()
    while True:
        if cv.waitKey(1) & 0xFF == ord('q'):
            break
        # The "size" of the center, used to determine if a line starts from the center (meaning it could be a hand)
        center_rad = 40
        ret,src = vid.read()
        img_center = (src.shape[1]/2,src.shape[0]/2)
        if src is None:
            print('Error opening image!')
            print('Usage: hough_circle.py [image_name -- default ' + default_file + '] \n')
            return -1
        gray = cv.cvtColor(src, cv.COLOR_BGR2GRAY)
        gray = cv.medianBlur(gray, 5)

        rows = gray.shape[0]
        # You can change the parameters of the HoughCircles, to make sure you find the circles most accurately
        circles = cv.HoughCircles(gray, cv.HOUGH_GRADIENT, 1, rows / 8,
                                  param1=100, param2=30,
                                  minRadius=200, maxRadius=250)
        curr_max = (0,0,0,math.inf)
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                cv.circle(src, (i[0], i[1]), i[2], (0, 0, 0), 3)
                if curr_max[3] > math.sqrt(math.pow(i[0]-img_center[0],2)+math.pow(i[1]-img_center[1],2)):
                    curr_max = i[0],i[1],i[2],math.sqrt(math.pow(i[0]-img_center[0],2)+math.pow(i[1]-img_center[1],2))
            cv.circle(src, (curr_max[0], curr_max[1]), curr_max[2], (0, 0, 0), 3)
            center = (curr_max[0],curr_max[1])
            cv.circle(src,center,7,(0,0,255),-1)
            # Crops to only their relevant parts, change this as you see fits
            # Its also possible to make the crop dynamic, but it isn't suggested, as the window size might fluctuate
            gray = gray[0:500,130:620]
            src = src[0:500, 130:620]
            center = (round(gray.shape[1]/2),round(gray.shape[0]/2))
            mask = np.zeros(gray.shape[:2],dtype="uint8")
            cv. circle(mask, center, radius, 255, -1)
            masked = cv.bitwise_and(gray,mask)
            # Changing the blur parameters will affect how much the program is sensitive to noise
            blurred = cv.GaussianBlur(masked, (7,7), 0)
            # The Canny filter parameters will probably need to be adjusted to help minimize distractions
            edges = cv.Canny(image=blurred, threshold1=30, threshold2=100)

            """ 
            Increasing the minLineLength will help to ignore small lines originating from the center
            Decreasing the minLineLength will help the program to see smaller lines, for example those of a pocket watch
            
            Changing the maxLineGap will affect how much tolerance the program has to disruptions in the image    
            """
            lines = cv.HoughLinesP(edges,1, np.pi / 180, 50, minLineLength=50, maxLineGap=25)
            diff_lines = []
            hours_hand = (0,math.inf,0,0,None,0)
            minutes_hand = (0, 0, 0, 0,None,0)
            if lines is not None:
                for line in lines:
                    x1,y1,x2,y2=line[0]
                    line_len = math.sqrt(math.pow(x1-x2,2)+math.pow(y1-y2,2))
                    if x1 != x2:
                        line_slope = (y2-y1)/(x2-x1)
                        line_angle = math.atan(line_slope)
                        skip = False
                    else:
                        # If the line is angled straight downwards or upwards, this sets the angle the line will default to
                        # This feature hasn't been tested at all, and probably needs a-lot of manipulation to get working.
                        line_angle = np.pi/2
                        skip = True
                    start_dist_center = math.sqrt(math.pow(x1-center[0],2)+math.pow(y1-center[1],2))
                    end_dist_center = math.sqrt(math.pow(x2-center[0],2)+math.pow(y2-center[1],2))
                    if start_dist_center <= center_rad or end_dist_center <= center_rad:
                        if start_dist_center <= center_rad and not skip:
                            if find_quadrant(center,x2,y2) == 1:
                                line_angle += np.pi/2
                            if find_quadrant(center,x2,y2) == 2:
                                line_angle = (3*np.pi)/2 + line_angle
                            elif find_quadrant(center,x2,y2) == 3:
                                line_angle = (3*np.pi)/2 + line_angle
                            elif find_quadrant(center,x2,y2) == 4:
                                line_angle = np.pi/2 + line_angle
                        elif end_dist_center <= center_rad and not skip:
                            if find_quadrant(center,x1,y1) == 1:
                                line_angle += np.pi/2
                            if find_quadrant(center,x1,y1) == 2:
                                line_angle = (3*np.pi)/2 + line_angle
                            elif find_quadrant(center,x1,y1) == 3:
                                line_angle = (3*np.pi)/2 + line_angle
                            elif find_quadrant(center,x1,y1) == 4:
                                line_angle = np.pi/2 + line_angle
                        new_line = True
                        for i in range(len(diff_lines)):
                            """
                            The math.radians(5) means the program will treat all lines whose angle is 5 radians from each other as the same
                            This can be changed to account for extra thick clock hands
                            """
                            if diff_lines[i][0]-math.radians(5) <= line_angle <= diff_lines[i][0]+math.radians(5):
                                new_line = False
                                if line_len > diff_lines[i][1]:
                                    diff_lines[i][1] = line_len
                                    diff_lines[i][0] = (diff_lines[i][0]*diff_lines[i][2]+line_angle)/(diff_lines[i][2]+1)
                                    diff_lines[i][2] += 1
                                    diff_lines[i][3] = x1
                                    diff_lines[i][4] = y1
                                    diff_lines[i][5] = x2
                                    diff_lines[i][6] = y2
                                break
                        if new_line:
                            diff_lines.append([line_angle,line_len,1,x1,y1,x2,y2])
            for i in diff_lines:
                cv.line(src, (i[3], i[4]),
                        (i[5], i[6]),
                        (0, 255, 0), 5)
                if i[1] > minutes_hand[1]:
                    minutes_hand = i
                if i[1] < hours_hand[1]:
                    hours_hand = i
            hour = math.floor((12*hours_hand[0])/(2*np.pi))
            dist_from_full = (12*hours_hand[0])/(2*np.pi)-hour
            minute = math.floor((60*minutes_hand[0])/(2*np.pi))

            """
            The 50 was picked practically at random, and is used to decide for cases where the hours hand is very close to a whole hour.
            It just means that if the minute is over 50, but the hour is just over a whole hour, reduce the hour by 1
            If you want to change the 50 figure, make sure to also change the 1/6 figure according the formula
            1-(x/60), with x being the minute.
            """
            if minute > 50 and dist_from_full < 1/6:
                hour -= 1

            if minute >= 60:
                minute = 0
                hour += 1
            if hour > 12:
                hour = 1
            if cv.waitKey(1) & 0xFF == ord(' '):
                # Saying the time when space is pressed, this can be changed as you will.
                # I suggest you keep in mind the pyttsx3 can sometimes be a bit janky, so just be somewhat careful.
                engine.say("Calculating the time...")
                engine.say("The time is")
                engine.say(str(hour) + ":" + str(minute).zfill(2))
                engine.runAndWait()
            src = cv.resize(src,(245,240))
            edges = cv.resize(edges,(245,240))
            gray = cv.resize(gray,(245,240))
            time_win = np.zeros([240,245],dtype="uint8")
            time_win = cv.cvtColor(time_win,cv.COLOR_GRAY2RGB)
            cv.putText(time_win, str(hour).zfill(2)+" : "+str(minute).zfill(2),(0,120),cv.FONT_HERSHEY_COMPLEX,2,(255,255,0))
            final_image_row_1 = np.hstack((cv.cvtColor(edges,cv.COLOR_GRAY2RGB),src))
            fina_image_row_2 = np.hstack((cv.cvtColor(gray,cv.COLOR_GRAY2RGB),time_win))
            final_image = np.vstack((final_image_row_1,fina_image_row_2))
            cv.imshow("final",final_image)
    return 0


def find_quadrant(center,x,y):
    if x >= center[0] and y < center[1]:
        return 1
    elif x < center[0] and y < center[1]:
        return 2
    elif x < center[0] and y >= center[1]:
        return 3
    elif x >= center[0] and y >= center[1]:
        return 4
    return 0


if __name__ == "__main__":
    main()