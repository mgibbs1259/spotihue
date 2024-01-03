import React from 'react';
import { usePostData } from '../hooks/usePostData';
import PrimaryButton from './PrimaryButton';
import ImageButton from './ImageButton';
import './ConfigureModal.css';

function HueConfigureModal({ isOpen, onClose, apiEndpoint }) {
  const { data, isLoading, error } = usePostData(apiEndpoint);

  return (
    <div className={`configure-modal ${isOpen ? 'open' : ''}`}>
      <div className="modal-content">
        <div className="modal-header">
          <ImageButton
              imageSrc={require('../assets/pink-cancel.png')}
              altText="X"
              onClick={onClose}
              height="50px"
              width="50px"
          />
        </div>
        {isLoading && <p>Loading...</p>}
        {error && <p>Error: {error.message}</p>}
        {data && (
          <div>
            <p>{data.data.message}</p>
          </div>)
        }
        <div className="modal-footer">
        <PrimaryButton 
            text="done" 
            fontSize="40px" 
            disabled={false} 
            onClick={onClose}
        />
        </div>
      </div>
    </div>
  );
}

export default HueConfigureModal;