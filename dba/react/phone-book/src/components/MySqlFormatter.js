import React, { Component } from 'react';
import SyntaxHighlighter from 'react-syntax-highlighter';
import sqlFormatter from 'sql-formatter';


class MySqlFormatter extends Component {
    constructor(props) {
        super(props)
    }

    render() {
        const { value } = this.props;
        const formattedSql = sqlFormatter.format(value)
        console.log(this.props.style)
        return (
            <SyntaxHighlighter
                language='sql' 
                style={this.props.style} 
                showLineNumbers={this.props.lineNumber} 
            >
                {formattedSql}
            </SyntaxHighlighter>
        );
    }
}

export default MySqlFormatter;
