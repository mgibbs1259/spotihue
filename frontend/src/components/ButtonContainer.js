import React from 'react';
import './ButtonContainer.css';

function ButtonContainer({ children }) {
  return (
    <div className="button-container">
      {children}
    </div>
  );
}

export default ButtonContainer;