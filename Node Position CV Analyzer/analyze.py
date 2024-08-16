import cv2
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from openpyxl import Workbook

SCALE_FACTOR = 41.9     # Pixels per mm
MIN_AREA = 50           # Minimum area of the contour in pixels
MAX_AREA = 5000         # Maximum area of the contour in pixels
BLACK_THRESHOLD = 100   # Threshold to identify black pixels, out of 255

def plotImg(img):
    if len(img.shape) == 2:
        plt.imshow(img, cmap='gray')
        plt.show()
    else:
        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        plt.show()

def analyze(image_path, output_folder, workbook):
    # Load the image
    img = cv2.imread(image_path)

    # Conversion to CMYK (just the K channel):
    # Convert to float and divide by 255:
    imgFloat = img.astype(float) / 255.

    # Calculate channel K:
    kChannel = 1 - np.max(imgFloat, axis=2)

    # Convert back to uint 8:
    kChannel = (255 * kChannel).astype(np.uint8)

    # Threshold image:
    _, binaryImage = cv2.threshold(kChannel, BLACK_THRESHOLD, 255, cv2.THRESH_BINARY)
    # plotImg(binaryImage)

    # Searching for contours on threshold img
    cnts, _ = cv2.findContours(binaryImage, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    i = 0   # index to tag the contours
    data = {}

    for c in cnts:
        area = cv2.contourArea(c)

        if area < MIN_AREA or area > MAX_AREA: 
            continue

        rect = cv2.minAreaRect(c) 
        box = cv2.boxPoints(rect)
        box = np.intp(box)
        (x, y), (w, h), angle = rect

        # ignores contours with aspect ratio thinner than 1:3 to avoid ruler tick marks
        if w/h < 1/3 or w/h > 3:
            continue

        cv2.drawContours(img,[box],0,(0,255,0),2)

        x_mm = round(x/SCALE_FACTOR, 3)
        y_mm = round(y/SCALE_FACTOR, 3)        

        # tags each contour with index and saves to data dict
        cv2.putText(img, f"{i}", (int(x+50), int(y)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 5)
        data[i] = (x_mm, y_mm)

        i+=1
        
        # additional img labels that are not needed for now
        # cv2.putText(img, f"x: {x/SCALE_FACTOR:.1f}", (int(x+50), int(y-20)), 
        #             cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2) 
        # cv2.putText(img, f"y: {y/SCALE_FACTOR:.1f}", (int(x+50), int(y+20)), 
        #             cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2) 
        # cv2.putText(img, f"area: {area}", (int(x), int(y)), 
        #             cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2) 

    cv2.putText(img, f"Filename: {str(image_path).split('/')[-1]}", (100, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 10) 
    cv2.putText(img, f"Scale Factor: {SCALE_FACTOR}", (100, 200), 
                    cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 10)

    # plotImg(img)
    # Save the final image to output folder and data to excel
    img_name = image_path.stem
    cv2.imwrite(f"{output_folder}/{img_name}_analyzed.jpg", img)
    ws = workbook.create_sheet(img_name)

    ws.append(["index","x_mm","y_mm"])
    for key, val in data.items():
        ws.append([key, val[0], val[1]])

if __name__ == '__main__':
    input_folder = Path(__file__).parent / "input"
    output_folder = Path(__file__).parent / "output"

    wb = Workbook() # to save the data

    # loop through all the images in the input folder using pathlib
    for file in Path(input_folder).glob("*.JPG"):
        print("Analyzing", file)
        analyze(image_path=file, output_folder=output_folder, workbook=wb)

    del wb["Sheet"]
    wb.save(f"{output_folder}/data.xlsx")