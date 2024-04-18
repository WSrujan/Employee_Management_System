# intership

A project where User/work gives attendance and their work status using python.

To do:
Create a form or interface where user inputs data.
Create a python script where data is processed into database / storage.
Create DataBase (Mysql?)

Data Flow

1.  Login Page (UI)
    User name (textbox)
    Password (Pasword)
    Email ID (Textbox)
    Register New Employ (Button)
    Forgot my Password (Button)

    (Script)
    Linking inputs to DataBase / Storage
    Verification of credentials
    Redirecting to new page after creating button

2.  SignUp Page (UI)
    Username (Textbox)
    Password (password)
    Retype Password (password)
    Email ID (Textbox)
    Retype Email ID (Textbox)
    Employ ID (Textbox)
    Job Title (Textbox)
    Contact Details (Textbox)
    Retype Contact Details (Textbox)
    Education(Textbox)
    Profile Picture (image) upload or Default
    Upload Button (image)

    (Script)
    Linking inputs to DataBase / Storage
    Verification of credentials
    Create a entrie in table
    Image storing in files

3.  Profile (UI)
    Name/Username (Text)
    Profile Picture (image)
    Employ ID (Number)
    Job Title (Text)
    Project Name (Text)
    Contact Details (Text)
    Education(Text)

    (Script)
    Showing data from DataBase

4.  Status Page (UI)
    Create a Project Button (Button)
    Project Selector (Dropdown box)
    Project Name (Text)
    Work Status / Diary (Textbox)
    Issues page (Textbox)
    Display remarks from admin
    Button to save

    (Script)
    Ability to create table / folder when new project button is clicked with default values.
    Showing Data from Storage
    Ability store data from textboxs
    Abilty to Increment Counters of Working Day and Offdays

5.  Forgot My Password Page (UI)
    Employ Number (Number)
    Email Id to send reset code (Email)
    Button to send (Button)

    (Script)
    Verification of details of Employ using database tables
    Sending Request to Database to create Reset code
    A method to send email containing reset code.

6.  SignUp Admin Page (UI)
    Username (Textbox)
    Password (password)
    Admin code (Number)
    Retype Password (password)
    Email ID (Textbox)
    Retype Email ID (Textbox)
    Employ ID (Textbox)
    Job Title (Textbox)
    Contact Details (Textbox)
    Retype Contact Details (Textbox)
    Education(Textbox)
    Profile Picture (image) upload or Default
    Upload Button (image)

    (Script)
    Linking inputs to DataBase / Storage
    Verification of credentials
    Create a entrie in table
    Image storing in files

7.  Admin Status Page (UI)
    Create Table with columms Employ ID, Employ Name, Project Name, Status, etc
    or
    Create a list of users registered as Employ
    Clicking name will open employ details and have admin section
    such as Accepted, rejected, comments,etc

    (Script)
    Interconnecting admin and employ table to show details to admin.
    storing remarks and displaying to respected employee
