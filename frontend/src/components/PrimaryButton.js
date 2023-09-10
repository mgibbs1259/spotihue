import React from 'react';
import PropTypes from 'prop-types';
import './PrimaryButton.css';

const PrimaryButton = ({ text, fontSize, disabled, onClick }) => {
  const handleButtonClick = () => {
    if (onClick) {
      onClick();
    }
  };

  const buttonStyle = {
    fontSize: fontSize,
  };

  return (
    <button className={`primary-button ${disabled ? 'primary-button-disabled' : ''}`} style={buttonStyle} onClick={handleButtonClick} disabled={disabled}>
      {text}
    </button>
  );
};

PrimaryButton.propTypes = {
  text: PropTypes.string.isRequired,
  fontSize: PropTypes.string.isRequired,
  disabled: PropTypes.bool, // Whether the button is disabled (greyed out)
  onClick: PropTypes.func, // Optional click handler
};

export default PrimaryButton;