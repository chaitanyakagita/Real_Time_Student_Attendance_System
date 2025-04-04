import os
import pickle
import numpy as np
import cv2
import face_recognition
import cvzone
import firebase_admin  #used to manage Firebase services like database, and storage.
from firebase_admin import credentials  #initialize the Firebase app using service account credentials.
from firebase_admin import db
from firebase_admin import storage
from datetime import datetime
import openpyxl


#Initializing Firebase & connecting to the Firebase Realtime Database and Storage Bucket.
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://studentattendance-d23dc-default-rtdb.firebaseio.com/",
    'storageBucket': "studentattendance-d23dc.appspot.com"
})

bucket = storage.bucket()  # Creates a reference to the Firebase Storage bucket, where images are stored.


cap = cv2.VideoCapture(0)

#Setting the resolution of the captured video to 640x480 pixels
cap.set(3, 640)
cap.set(4, 480)

imgBackground = cv2.imread('Resources/background.png')


#Importing the mode images into a list
folderModePath = 'Resources/Modes'
modePathList = os.listdir(folderModePath)  #Lists all files in the mode images folder
imgModeList = []   #to store the mode images.
for path in modePathList:
    imgModeList.append(cv2.imread(os.path.join(folderModePath, path)))


# Load the encoding file
print("Loading Encode File ...")
file = open('EncodeFile.p', 'rb')  #Opens the encoded face data file in read-binary mode.
encodeListKnownWithIds = pickle.load(file)
file.close()
encodeListKnown, studentIds = encodeListKnownWithIds
print(studentIds)
print("Encode File Loaded")


modeType = 0
counter = 0   #Tracks the number of iterations after a face is recognized.
id = -1
imgStudent = []  #holds the image of the recognized student.

# Load or create Excel file
excel_file_path = 'Attendance.xlsx'
if not os.path.exists(excel_file_path):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Attendance'
    # Create headers in the first row
    sheet.append(["Student ID", "Name", "Branch", "Section", "Total attendance", "Time of Entry"])
    workbook.save(excel_file_path)

while True:
    success, img = cap.read()

    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)  #Resizes img to 1/4 of its original size for faster processing.
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB) #openCV-->BGR, faceRecognition-->RGB

    faceCurFrame = face_recognition.face_locations(imgS)  #Detects faces in the current frame.
    encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)  #Encodes the detected faces into numerical data.

    imgBackground[162:162 + 480, 55:55 + 640] = img
    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

    #If faces are detected in the current frame:
    if faceCurFrame:
        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
            #print("matches",matches)
            #print("faceDistance",faceDis)
            matchIndex = np.argmin(faceDis)

            y1, x2, y2, x1 = faceLoc    #Unpacks the face location.
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
            bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
            imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)

            #If a match is found:
            if matches[matchIndex]:
                id = studentIds[matchIndex]
                if counter == 0:  #If this is the 1st iteration after recognition:
                    cvzone.putTextRect(imgBackground, "Loading...", (275, 400),0.8, 2 , font=cv2.FONT_HERSHEY_DUPLEX)
                    cv2.imshow("Face Attendance", imgBackground)
                    cv2.waitKey(1)
                    counter = 1
                    modeType = 1   #Switches to the next mode.

        if counter != 0:   #indicates a face was recognized
            if counter == 1:
                # Get the Data
                studentInfo = db.reference(f'Students/{id}').get()
                print(studentInfo)
                # Get the Image from the storage
                blob = bucket.get_blob(f'Images/{id}.png')

                if blob is not None:  #image exists
                    array = np.frombuffer(blob.download_as_string(), np.uint8)  #Converts the image to a NumPy array.
                    imgStudent = cv2.imdecode(array, cv2.IMREAD_COLOR) #Decodes the image to its original color format.
                    imgStudent = cv2.resize(imgStudent, (216, 216))
                else:
                    print(f"No image found for student ID {id}")
                    imgStudent = np.zeros((216, 216, 3), dtype=np.uint8)  # Placeholder black image

                # Update data of attendance
                datetimeObject = datetime.strptime(studentInfo['last_attendance_time'], "%Y-%m-%d %H:%M:%S")
                secondsElapsed = (datetime.now() - datetimeObject).total_seconds() #Calc the sec's passed since last attendance.
                #print(secondsElapsed)


                if secondsElapsed > 60:
                    ref = db.reference(f'Students/{id}')
                    studentInfo['total_attendance'] += 1
                    ref.child('total_attendance').set(studentInfo['total_attendance'])  #Updates the total attendance
                    ref.child('last_attendance_time').set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                    # Append the attendance record to the Excel file
                    workbook = openpyxl.load_workbook(excel_file_path)
                    sheet = workbook.active
                    sheet.append([id, studentInfo['name'],studentInfo['major'], studentInfo['standing'], studentInfo['total_attendance'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                    workbook.save(excel_file_path)

                else:
                    modeType = 3  #indicating recent attendance
                    counter = 0
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

            if modeType != 3:
                if 10 < counter < 20:
                    modeType = 2  #indicating successful recognition.

                imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                if counter <= 10:
                    cv2.putText(imgBackground, str(studentInfo['total_attendance']), (861, 125),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo['major']), (1006, 550),
                                cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(id), (1006, 493),
                                cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo['standing']), (910, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, str(studentInfo['year']), (1025, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, str(studentInfo['starting_year']), (1125, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)

                    (w, h), _ = cv2.getTextSize(studentInfo['name'], cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                    offset = (414 - w) // 2
                    cv2.putText(imgBackground, str(studentInfo['name']), (808 + offset, 445),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)

                    imgBackground[175:175 + 216, 909:909 + 216] = imgStudent  #Places student img on the background.

                counter += 1

                if counter >= 20:
                    counter = 0
                    modeType = 0
                    studentInfo = []  #Clear the student info
                    imgStudent = []  #Clear the student img
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]  #Reset the background img
    else:
        modeType = 0
        counter = 0

    cv2.imshow("Face Attendance", imgBackground)

    # Quit when 'q' key is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
