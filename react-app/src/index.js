import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';
import './index.css';


// *************************************************************

// var rootElement = document.createElement('div');
// rootElement.style.display = 'flex';
// rootElement.style.alignItems = 'center';
//
//
// var heading = document.createElement('h1');
//
// var textNode = document.createTextNode('Welcome to Raw React');
//
// var img = document.createElement('img');
// img.setAttribute('src', './src/logo.svg');
// img.setAttribute('width', '64px');
// img.setAttribute('height', '64px');
//
// heading.appendChild(textNode);
// rootElement.appendChild(img);
// rootElement.appendChild(heading);
//
// document.body.insertBefore(rootElement, document.getElementById('root'));


// *************************************************************

// var rootElement = document.createElement('div');
// var heading = document.createElement('h2');
// var textNode = document.createTextNode('Hello World');
// //
// heading.appendChild(textNode);
// rootElement.appendChild(heading);
// //
// document.body.insertBefore(rootElement, document.getElementById('root'));

// *************************************************************

// var rootElement =
//   React.createElement('div', {},
//     React.createElement('h2', {}, 'Hello World')
// )
//
// ReactDOM.render(
//   rootElement, document.getElementById('root')
// )

// *************************************************************

// var rootElement =
//   React.createElement('div', {},
//     React.createElement('h1', {}, "Contacts"),
//     React.createElement('ul', {},
//       React.createElement('li', {},
//         React.createElement('h2', {}, "Moaaz Sidat"),
//         React.createElement('a', {href: 'mailto:moaazsidat@freshbooks.com'}, 'moaazsidat@freshbooks.com.com')
//       ),
//       React.createElement('li', {},
//         React.createElement('h2', {}, "Freshy McFreshface"),
//         React.createElement('a', {href: 'mailto:fresh@freshbooks.com'}, 'joe@example.com')
//       )
//     )
//   )
//
// ReactDOM.render(
//   rootElement, document.getElementById('root')
// )

// *************************************************************

// Hmm, that's nice but what about using data from a json or api

// var people = [
//   {
//     key: 1,
//     name: 'Moaaz Sidat',
//     email: 'moaazsidat@freshbooks.com',
//   },
//   {
//     key: 2,
//     name: 'Freshy McFreshface',
//     email: 'freshy@freshbooks.com',
//   },
//   {
//     key: 2,
//     name: 'Bad McFreshface',
//   },
// ]
//
// var listElements = people
//   .filter((person) => (person.email))
//   .map((person) => (
//     React.createElement('li', { key: person.key },
//       React.createElement('h2', {}, person.name),
//       React.createElement('a', { href:'mailto:'+person.email }, person.email)
//     )
//   ))
//
// var rootElement =
//   React.createElement('div', {},
//     React.createElement('h1', {}, 'Contacts'),
//       React.createElement('ul', {}, listElements)
// )
//
// ReactDOM.render(
//   rootElement, document.getElementById('root')
// )

// *************************************************************

// var people = [
//   {
//     key: 1,
//     name: 'Moaaz Sidat',
//     email: 'moaazsidat@freshbooks.com',
//   },
//   {
//     key: 2,
//     name: 'Freshy McFreshface',
//     email: 'freshy@freshbooks.com',
//   },
//   {
//     key: 2,
//     name: 'Bad McFreshface',
//   },
// ]
//
// var Person = React.createClass({
//   // propTypes: {
//   //   name: React.PropTypes.string,
//   //   email: React.PropTypes.string,
//   // }
//   render: function() {
//     return (
//       <li>
//         <h2>{this.props.name}</h2>
//         <a href={'mailto:' + this.props.email}>{this.props.email}</a>
//       </li>
//     );
//   }
// })
//
// var personElements = people
//   .filter((person) => (person.email))
//   .map((person) => (
//     React.createElement(Person, { key: person.key, name: person.name, email: person.email })
//   ))
//
// var rootElement =
//   React.createElement('div', {},
//     React.createElement('h1', {}, 'Contacts'),
//       React.createElement('ul', {}, personElements)
// )
//
// ReactDOM.render(
//   rootElement, document.getElementById('root')
// )

// *************************************************************
//
// var people = window.people = [
//   {
//     key: 1,
//     name: 'Moaaz Sidat',
//     email: 'moaazsidat@freshbooks.com',
//   },
//   {
//     key: 2,
//     name: 'Freshy McFreshface',
//     email: 'freshy@freshbooks.com',
//   },
//   {
//     key: 2,
//     name: 'Bad McFreshface',
//   },
// ]
// //
// var Person = React.createClass({
//   render: function() {
//     return (
//       <li>
//         <h2>{this.props.name}</h2>
//         <a href={'mailto:' + this.props.email }>{this.props.email}</a>
//       </li>
//     )
//   }
// })
//
// var personElements = people
//   .filter((person) => (person.email))
//   .map((person) => (
//     React.createElement(Person, { key: person.key, name: person.name, email: person.email })
//   ))
//
// var rootElement =
//   React.createElement('div', {},
//     React.createElement('h1', {}, 'Contacts'),
//       React.createElement('ul', {}, personElements)
// )
//
// ReactDOM.render(
//   rootElement, document.getElementById('root')
// )

// *************************************************************

var people = window.people = [
  {
    key: 1,
    name: 'Moaaz Sidat',
    email: 'moaazsidat@freshbooks.com',
  },
  {
    key: 2,
    name: 'Freshy McFreshface',
    email: 'freshy@freshbooks.com',
  },
  {
    key: 2,
    name: 'Bad McFreshface',
  },
]

var Person = React.createClass({
  render: function() {
    return (
      <li>
        <h2>{this.props.name}</h2>
        <a href={'mailto:' + this.props.email }>{this.props.email}</a>
      </li>
    )
  }
})

var People = React.createClass({

  render: function() {
    var personElements = this.props.people
      .filter((person) => (person.email))
      .map((person) => (
        <Person
          className='Foo'
          key={person.key}
          name={person.name}
          email={person.email}
        />
      ))

    return (
      <div>
        <h1>Contacts</h1>
        <ul>{personElements}</ul>
      </div>
    )
  }
})

var RootElement = React.createClass({
  render: function() {
    return (
      <People people={this.props.people}/>
    )
  }
})

var Moaaz_string = 'string'
var Moaaz_num = 23
var arr = [1, 2]
var obj = {}

var UIEl = <UIElement />

ReactDOM.render(
  <RootElement people={people}/>, document.getElementById('root')
)

// *************************************************************



// ReactDOM.render(
//   <App />,
//   document.getElementById('root')
// );
