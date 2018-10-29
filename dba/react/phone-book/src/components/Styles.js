import React, { Component, Fragment } from 'react'; 

const availableStyles = [
  'agate',
  'androidstudio',
  'arduino-light',
  'arta',
  'ascetic',
  'atelier-cave-dark',
  'atelier-cave-light',
  'atelier-dune-dark',
  'atelier-dune-light',
  'atelier-estuary-dark',
  'atelier-estuary-light',
  'atelier-forest-dark',
  'atelier-forest-light',
  'atelier-heath-dark',
  'atelier-heath-light',
  'atelier-lakeside-dark',
  'atelier-lakeside-light',
  'atelier-plateau-dark',
  'atelier-plateau-light',
  'atelier-savanna-dark',
  'atelier-savanna-light',
  'atelier-seaside-dark',
  'atelier-seaside-light',
  'atelier-sulphurpool-dark',
  'atelier-sulphurpool-light',
  'brown-paper',
  'codepen-embed',
  'color-brewer',
  'dark',
  'darkula',
  'docco',
  'far',
  'foundation',
  'github-gist',
  'github',
  'googlecode',
  'grayscale',
  'hopscotch',
  'hybrid',
  'idea',
  'ir-black',
  'kimbie.dark',
  'kimbie.light',
  'magula',
  'mono-blue',
  'monokai-sublime',
  'monokai',
  'obsidian',
  'paraiso-dark',
  'paraiso-light',
  'pojoaque',
  'railscasts',
  'rainbow',
  'school-book',
  'solarized-dark',
  'solarized-light',
  'sunburst',
  'tomorrow-night-blue',
  'tomorrow-night-bright',
  'tomorrow-night-eighties',
  'tomorrow-night',
  'tomorrow',
  'vs',
  'xcode',
  'xt256',
  'zenburn'
];

class Styles extends Component {
    constructor(props) {
        super(props)
        this.state = {
            style: undefined,
            selected: undefined
        }
    }

    handleChange = (e) => {
        const selected = e.target.value
        const style = require(`react-syntax-highlighter/styles/hljs/${selected}`).default
        console.log(`style: ${selected}`)
        this.setState({style: style, selected: selected})
        this.props.onChange(style)
    } 

    render() {
        console.log(`SELECTED: ${this.state.selected || this.props.defaultSelected}`)
        return (
            <Fragment>
                <label htmlFor="sourceCodeStyle">Source Code Style:</label>
                <select
                    value={this.state.selected || this.props.defaultSelected}
                    onChange={this.handleChange}>
                    {
                         availableStyles.map(s => 
                            <option key={s} value={s}>{s}</option>)
                    }
                </select>
            </Fragment>
        
        );
    }
}

export default Styles;
