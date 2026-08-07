-- Create majors table
CREATE TABLE IF NOT EXISTS majors (
    major_id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_name TEXT NOT NULL,
    department TEXT NOT NULL
);

-- Create students table
CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    enrollment_year INTEGER NOT NULL,
    gpa REAL,
    major_id INTEGER,
    FOREIGN KEY (major_id) REFERENCES majors(major_id)
);

-- Create courses table
CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name TEXT NOT NULL,
    credits INTEGER NOT NULL,
    department TEXT NOT NULL
);

-- Create enrollments table
CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    course_id INTEGER,
    semester TEXT NOT NULL,
    grade TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- Create professors table
CREATE TABLE IF NOT EXISTS professors (
    professor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    email TEXT UNIQUE
);

-- Create teaches table
CREATE TABLE IF NOT EXISTS teaches (
    professor_id INTEGER,
    course_id INTEGER,
    semester TEXT NOT NULL,
    PRIMARY KEY (professor_id, course_id, semester),
    FOREIGN KEY (professor_id) REFERENCES professors(professor_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- Insert Majors (ignore if already inserted)
INSERT OR IGNORE INTO majors (major_id, major_name, department) VALUES (1, 'Computer Science', 'FCAI');
INSERT OR IGNORE INTO majors (major_id, major_name, department) VALUES (2, 'Artificial Intelligence', 'FCAI');
INSERT OR IGNORE INTO majors (major_id, major_name, department) VALUES (3, 'Electrical Engineering', 'Engineering');

-- Insert Students
INSERT OR IGNORE INTO students (student_id, name, enrollment_year, gpa, major_id) VALUES (1, 'M. Jamal', 2023, 3.85, 1);
INSERT OR IGNORE INTO students (student_id, name, enrollment_year, gpa, major_id) VALUES (2, 'Abdul Wasay', 2024, 3.65, 2);
INSERT OR IGNORE INTO students (student_id, name, enrollment_year, gpa, major_id) VALUES (3, 'Syed Mujtaba Gillani', 2023, 3.90, 1);
INSERT OR IGNORE INTO students (student_id, name, enrollment_year, gpa, major_id) VALUES (4, 'Alice Smith', 2022, 2.80, 3);
INSERT OR IGNORE INTO students (student_id, name, enrollment_year, gpa, major_id) VALUES (5, 'Bob Jones', 2025, 3.10, 1);

-- Insert Courses
INSERT OR IGNORE INTO courses (course_id, course_name, credits, department) VALUES (1, 'Advanced Database Management Systems', 4, 'FCAI');
INSERT OR IGNORE INTO courses (course_id, course_name, credits, department) VALUES (2, 'Introduction to Artificial Intelligence', 3, 'FCAI');
INSERT OR IGNORE INTO courses (course_id, course_name, credits, department) VALUES (3, 'Linear Circuits', 3, 'Engineering');
INSERT OR IGNORE INTO courses (course_id, course_name, credits, department) VALUES (4, 'Software Engineering', 3, 'FCAI');

-- Insert Enrollments
INSERT OR IGNORE INTO enrollments (enrollment_id, student_id, course_id, semester, grade) VALUES (1, 1, 1, 'Fall 2025', 'A');
INSERT OR IGNORE INTO enrollments (enrollment_id, student_id, course_id, semester, grade) VALUES (2, 2, 2, 'Fall 2025', 'B+');
INSERT OR IGNORE INTO enrollments (enrollment_id, student_id, course_id, semester, grade) VALUES (3, 3, 1, 'Fall 2025', 'A');
INSERT OR IGNORE INTO enrollments (enrollment_id, student_id, course_id, semester, grade) VALUES (4, 4, 3, 'Spring 2025', 'C');
INSERT OR IGNORE INTO enrollments (enrollment_id, student_id, course_id, semester, grade) VALUES (5, 1, 4, 'Spring 2025', 'A-');
INSERT OR IGNORE INTO enrollments (enrollment_id, student_id, course_id, semester, grade) VALUES (6, 5, 1, 'Fall 2025', 'F');
INSERT OR IGNORE INTO enrollments (enrollment_id, student_id, course_id, semester, grade) VALUES (7, 5, 4, 'Fall 2025', 'F');

-- Insert Professors
INSERT OR IGNORE INTO professors (professor_id, name, department, email) VALUES (1, 'Sir Obaidullah', 'FCAI', 'obaidullah@air.edu.pk');
INSERT OR IGNORE INTO professors (professor_id, name, department, email) VALUES (2, 'Dr. Sarah Khan', 'Engineering', 'sarah.khan@air.edu.pk');

-- Insert Teaches
INSERT OR IGNORE INTO teaches (professor_id, course_id, semester) VALUES (1, 1, 'Fall 2025');
INSERT OR IGNORE INTO teaches (professor_id, course_id, semester) VALUES (1, 4, 'Spring 2025');
INSERT OR IGNORE INTO teaches (professor_id, course_id, semester) VALUES (2, 3, 'Spring 2025');
