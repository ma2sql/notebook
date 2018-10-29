// import React, { Component } from 'react';
// import logo from './logo.svg';
// import './App.css';
import React, { Component } from 'react';
import MySqlFormatter from './components/MySqlFormatter';
import MySqlFormatterForm from './components/MySqlFormatterForm';
import LineNumber from './components/LineNumber';
import Styles from './components/Styles';


class App extends Component {
  state = {
      sql: '',
      showLineNumber: false,
      style: require(`react-syntax-highlighter/styles/hljs/github`).default,
      selectedStyle: 'github'
  }

  handleChange = (formattedSql) => {
      this.setState({
          sql: formattedSql
      });     
  }

  handleLineNumber = (a) => {
      this.setState({showLineNumber: a})
  }

  render() {
    return (
        <div>
            <Styles 
                defaultSelected={this.state.selectedStyle}
                onChange={(e) => {
                                  this.setState({style: e});
                                  console.log(e);
                             }} />
            <br/>
            <LineNumber onChange={this.handleLineNumber}/>
            <div>
                <div style={{paddingTop: 20, display: 'flex'}}>
                    <MySqlFormatterForm onChange={this.handleChange} initSql='SELECT * FROM information_schema.columns'/>
                    <div style={{flex: 1, width: '50%'}}>
                        <MySqlFormatter value={this.state.sql} lineNumber={this.state.showLineNumber} style={this.state.style} />
                    </div>
                </div>
            </div>
        </div>
    );
  }
}

export default App
