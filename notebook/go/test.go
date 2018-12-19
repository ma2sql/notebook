package main

import (
    "database/sql"
    "fmt"
    "log"
    _ "github.com/go-sql-driver/mysql"
)


type User struct {
    user string
    host string
    password string
}


func GetDBConn(user string, password string, host string, port int) (*sql.DB) {
    connStr := fmt.Sprintf("%s:%s@tcp(%s:%d)/mysql", user, password, host, port)
    db, err := sql.Open("mysql", connStr)
    if err != nil {
        panic(err.Error())
    }
    return db
}


func IsExistUser(db *sql.DB, user string, host string) bool {
    rows, err := db.Query("SELECT COUNT(*) FROM mysql.user WHERE user = ? AND host = ?", user, host)
    if err != nil {
        panic(err.Error())
    }
    defer rows.Close()

    var count int = 0
    for rows.Next() {
        err := rows.Scan(&count)
        if err != nil {
            log.Fatal(err)
        }
    }
    return count == 1
}


func CreateUser(db *sql.DB, user string, host string, password string) {
    createSqlStr := fmt.Sprintf("CREATE USER '%s'@'%s' IDENTIFIED BY '%s'", user, host, password)
    rows, err := db.Query(createSqlStr)
    if err != nil {
        panic(err.Error())
    }
    defer rows.Close()
}


func GrantAdminUser(db *sql.DB, user string, host string) {
    createSqlStr := fmt.Sprintf("GRANT ALL ON *.* TO '%s'@'%s' WITH GRANT OPTION", user, host)
    rows, err := db.Query(createSqlStr)
    if err != nil {
        panic(err.Error())
    }
    defer rows.Close()
}


func PasswordChange(db *sql.DB, user string, host string, password string) {
    createSqlStr := fmt.Sprintf("SET PASSWORD FOR '%s'@'%s' = '%s'", user, host, password)
    rows, err := db.Query(createSqlStr)
    if err != nil {
        panic(err.Error())
    }
    defer rows.Close()
}


func AddUser(db *sql.DB, user *User) {
    log.Printf("Check if user exists: '%s'@'%s'\n", user.user, user.host)
    if !IsExistUser(db, user.user, user.host) {
        log.Printf("Create User: '%s'@'%s'\n", user.user, user.host)
        CreateUser(db, user.user, user.host, user.password)
    }
    log.Printf("Grant User: '%s'@'%s'\n", user.user, user.host)
    GrantAdminUser(db, user.user, user.host)
    log.Printf("Change Password: '%s'@'%s'\n", user.user, user.host)
    PasswordChange(db, user.user, user.host, user.password)
}


func main() {
    users := []User {
                 User{"sysbench1", "%", "sysbench1"},
                 User{"sysbench2", "%", "sysbench2"},
                 User{"sysbench3", "%", "sysbench3"},
                 User{"sysbench4", "%", "sysbench4"},
                 User{"sysbench5", "%", "sysbench5"},
             }

    // sql.DB 객체 생성
	log.Println("Create DB Connection")
    db := GetDBConn("sysbench", "sysbench", "127.0.0.1", 3306)
    defer db.Close()

    for _, user := range users {
        AddUser(db, &user)
    }
}

