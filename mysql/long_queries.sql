SELECT    T1.trx_id
        , T1.trx_state
        , NOW() AS current
        , T1.trx_started
        , TIMEDIFF(NOW(), T1.trx_started) as elapsed
        , T1.trx_query
        , T1.trx_operation_state
        , T2.PROCESSLIST_ID AS CONNECTION_ID
        , T2.THREAD_ID AS THREAD_ID
        , T2.PROCESSLIST_USER
        , T2.PROCESSLIST_HOST
        , T2.PROCESSLIST_TIME
        , T2.PROCESSLIST_INFO AS CURRENT_STATEMENT
        , T3.SQL_TEXT AS LAST_STATEMENT
FROM    INFORMATION_SCHEMA.INNODB_TRX T1
        INNER JOIN performance_schema.threads T2 on T2.PROCESSLIST_ID = T1.trx_mysql_thread_id
        INNER JOIN performance_schema.events_statements_current T3 on T3.thread_id = T2.thread_id
ORDER   BY  T1.trx_started