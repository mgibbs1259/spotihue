import React from 'react';
import './ImageButton.css';

function ImageButton({ imageSrc, altText, height, width, onClick }) { 
    return (
        <button className="image-button" onClick={onClick}>
        <img className="image-icon" src={imageSrc} alt={altText} style={{ height: height, width: width }}/>
        </button>
    );
}

export default ImageButton;