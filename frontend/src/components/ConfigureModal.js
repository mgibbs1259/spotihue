import React from 'react';
import { useData } from '../hooks/useData';
import PrimaryButton from './PrimaryButton';
import './ConfigureModal.css';

function ConfigureModal({ isOpen, onClose, apiEndpoint }) {
  const { data, isLoading, error } = useData(apiEndpoint);

  return (
    <div className={`configure-modal ${isOpen ? 'open' : ''}`}>
      <div className="modal-content">
        {isLoading && <p>Loading...</p>}
        {error && <p>Error: {error.message}</p>}
        {data && (
          <div>
            <p>Data: {data}</p>
          </div>
        )}
        <div className="modal-footer">
        <PrimaryButton text="done" fontSize="40px" disabled={false} onClick={onClose}></PrimaryButton>
        </div>
      </div>
    </div>
  );
}

export default ConfigureModal;