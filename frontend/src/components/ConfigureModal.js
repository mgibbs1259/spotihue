import React from 'react';
import PrimaryButton from './PrimaryButton';
import './ConfigureModal.css';

function ConfigureModal({ isOpen, onClose, children }) {
  return (
    <div className={`configure-modal ${isOpen ? 'open' : ''}`}>
      <div className="modal-content">
        {children}
        <div className="modal-footer">
        <PrimaryButton text="done" fontSize="40px" disabled={false} onClick={onClose}></PrimaryButton>
        </div>
      </div>
    </div>
  );
}

export default ConfigureModal;