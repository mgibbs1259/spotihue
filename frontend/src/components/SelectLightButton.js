import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './SelectLightButton.css';
import lightSelectedImage from '../assets/light-selected.png';
import lightDeselectedImage from '../assets/light-deselected.png';
import lightErrorImage from '../assets/light-error.png';

const SelectLightButton = ({ lightName, onClick }) => {
    const hasLightName = !!lightName;
    const [selected, setSelected] = useState(false);

    const handleButtonClick = () => {
      setSelected(!selected);
      if (onClick) {
          onClick();
        }
    };

    const imageSource = hasLightName ? (selected ? lightSelectedImage : lightDeselectedImage): lightErrorImage;

    const buttonClasses = [
      'select-light-button',
      hasLightName ? (selected ? 'select-light-button-clicked' : 'select-light-button-not-clicked'): 'select-light-button-no-lights',
    ].join(' ');

    const buttonText = hasLightName ? lightName : 'no lights available';

    return (
        <div className="select-light-button-container">
            <img src={imageSource} alt="light bulb" className="light-bulb-image" />
            <button
                className={buttonClasses}
                onClick={handleButtonClick}
                disabled={!hasLightName}
            >
                {buttonText}
            </button>
        </div>
    );
  };
  
  SelectLightButton.propTypes = {
    lightName: PropTypes.string.isRequired,
    onClick: PropTypes.func, // Optional click handler
  };
  
  export default SelectLightButton;