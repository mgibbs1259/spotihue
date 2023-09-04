import React, { useEffect } from 'react';
import { useGetData } from '../hooks/useGetData';
import PrimaryButton from './PrimaryButton';
import './ConfigureModal.css';

function useAuthorizeLink(apiEndpoint) {
  const { data, isLoading, error } = useGetData(apiEndpoint);

  useEffect(() => {
    if (data && !isLoading && !error) {
      // Open the URL in a new tab
      window.open(data.data.data.auth_url, '_blank');
    }
  }, [data]);

  return { data, isLoading, error };
}

function SpotifyConfigureModal({ isOpen, onClose, apiEndpoint }) {
  const { data, isLoading, error } = useAuthorizeLink(apiEndpoint);

  return (
    <div className={`configure-modal ${isOpen ? 'open' : ''}`}>
      <div className="modal-content">
        {isLoading && <p>Loading...</p>}
        {error && <p>Error: {error.message}</p>}
        {data && (
          <div>
            <p>{data.data.message}</p>
          </div>
        )}
        <div className="modal-footer">
        <PrimaryButton text="done" fontSize="40px" disabled={false} onClick={onClose}></PrimaryButton>
        </div>
      </div>
    </div>
  );
}

export default SpotifyConfigureModal;