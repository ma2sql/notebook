import React, { Component } from 'react';
import MySqlFormatter from './MySqlFormatter';
import sqlFormatter from 'sql-formatter';
import PropTypes from 'prop-types';

class MySqlFormatterForm extends Component {
    constructor(props) {
        super(props)
        this.state = {
            sql: this.props.initSql || ''
        }
        this.handleChange = this.handleChange.bind(this)
    }

    handleChange = (e) => {
        const sql = e.target.value
        this.props.onChange(sql)
        this.setState({sql: sql})
    }

    componentWillMount() {
        const sql = this.props.initSql
        this.props.onChange(sql)
        this.setState({sql: sql})
    }

    render() {
        return (
            <textarea
                style={{flex: 1, marginTop: 11}}
                value={this.state.sql} 
                onChange={this.handleChange} 
                rows="40" cols="100" />
        );
    }
}

export default MySqlFormatterForm;
