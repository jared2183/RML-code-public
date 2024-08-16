import cv2 
from pathlib import Path
import numpy as np

# SCALE_FACTOR (pixels per mm)
SCALE_FACTOR = 41.9

def analyze(image_path, outpath):
    # Load the image 
    img = cv2.imread(image_path) 

    # Convert the image to grayscale 
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) 
    cv2.imwrite("grayscale_output.jpg", gray)    

    # Apply a threshold to the image to 
    # separate the objects from the background
    ret, thresh = cv2.threshold( 
        gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)

    cv2.imwrite("threshhold_output.jpg", thresh)    

    # Find the contours of the objects in the image 
    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Loop through the contours and calculate the area of each object 
    for cnt in contours: 
        area = cv2.contourArea(cnt) 
        if area < 100: 
            continue
        # Draw a bounding box around each 
        # object and display the dimensions on the image 
        rect = cv2.minAreaRect(cnt) 
        box = cv2.boxPoints(rect)
        box = np.intp(box)
        (x, y), (w, h), angle = rect
        # print(f"x: {x}, y: {y}, w: {w}, h: {h}, angle: {angle}")
        cv2.drawContours(img,[box],0,(0,255,0),2)

        # makes sure height is greater than width
        if h < w: 
            w, h = h, w            
        
        cv2.putText(img, f"w: {w/SCALE_FACTOR:.3f}", (int(x), int(y)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2) 
        cv2.putText(img, f"h: {h/SCALE_FACTOR:.3f}", (int(x), int(y-40)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2) 

    # Show the final image with the bounding boxes 
    # and areas of the objects overlaid on top 
    # cv2.imshow('image', img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    cv2.putText(img, f"Filename: {image_path.split('/')[-1]}", (100, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 10) 
    cv2.putText(img, f"Scale Factor: {SCALE_FACTOR}", (100, 200), 
                    cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 10) 

    # Save the final image to output folder
    cv2.imwrite(outpath, img)    

if __name__ == '__main__':
    input_folder = '/Users/jaredmyang/Documents/GitHub/RML-gcode-generator/CV Measurer/input'
    output_folder = '/Users/jaredmyang/Documents/GitHub/RML-gcode-generator/CV Measurer/output'

    # loop through all the images in the input folder using pathlib
    for file in Path(input_folder).iterdir():
        if file.is_file() and file.suffix == '.JPG':
            print("Analyzing", file)
            analyze(image_path=str(file), outpath=f"{output_folder}/{file.stem}_analyzed.jpg")