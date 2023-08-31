import React from 'react';
import PropTypes from 'prop-types';
import './GreenBorderButton.css';

const GreenBorderButton = ({ text, fontSize, onClick }) => {
  const handleButtonClick = () => {
    if (onClick) {
      onClick();
    }
  };

  const buttonStyle = {
    fontSize: fontSize,
  };

  return (
    <button className="green-border-button" style={buttonStyle} onClick={handleButtonClick}>
      {text}
    </button>
  );
};

GreenBorderButton.propTypes = {
  text: PropTypes.string.isRequired,
  fontSize: PropTypes.string.isRequired,
  onClick: PropTypes.func, // Optional click handler for API request
};

export default GreenBorderButton;