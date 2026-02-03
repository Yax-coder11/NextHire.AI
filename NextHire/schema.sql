CREATE TABLE users (
    email TEXT PRIMARY KEY,
    password TEXT
);


CREATE TABLE resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT,
    name TEXT,
    phone TEXT,
    email TEXT,
    degree TEXT,
    cgpa TEXT,
    skills TEXT,
    projects TEXT,
    file_path TEXT,
    about_yourself TEXT,
    github_username TEXT,
    city TEXT
);

CREATE TABLE education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id INTEGER,
    degree TEXT,
    institution TEXT,
    start_year TEXT,
    end_year TEXT,
    description TEXT,
    FOREIGN KEY (resume_id) REFERENCES resumes (id)
);
 