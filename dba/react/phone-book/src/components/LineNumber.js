import React, { Component, Fragment } from 'react';


class LineNumber extends Component {
    constructor(props) {
        super(props)
        this.state = {
            showLineNumbers: false
        }
        this.handleChange = this.handleChange.bind(this) 
    }

    handleChange = (e) => {
        this.setState({showLineNumbers: !this.state.showLineNumbers});
        this.props.onChange(!this.state.showLineNumbers);
    }

    render() {
        return (
            <Fragment>
                <label htmlFor="showLineNumbers">Show Line Numbers:</label>
                <input 
                    type="checkbox"
                    checked={this.state.showLineNumbers}
                    onChange={this.handleChange}
                />
            </Fragment>
        );
    }    
}

export default LineNumber; 
