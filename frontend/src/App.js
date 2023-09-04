import './App.css';
import axios from 'axios';
import React, { useState, useEffect } from 'react';
import ButtonContainer from './components/ButtonContainer';
import HueConfigureModal from './components/HueConfigureModal';
import SpotifyConfigureModal from './components/SpotifyConfigureModal';
import PrimaryButton from './components/PrimaryButton';

function App() {
  const [apiReadyResponse, setApiReadyResponse] = useState(null);
  const [isHueModalOpen, setIsHueModalOpen] = useState(false);
  const [isSpotifyModalOpen, setIsSpotifyModalOpen] = useState(false);

  const openHueModal = () => {
    setIsHueModalOpen(true);
  };

  const closeHueModal = () => {
    setIsHueModalOpen(false);
  };

  const openSpotifyModal = () => {
    setIsSpotifyModalOpen(true);
  };

  const closeSpotifyModal = () => {
    setIsSpotifyModalOpen(false);
  };

  // Use useEffect to make an API call on initial page load
  useEffect(() => {
    // Function to fetch data from API
    const fetctConfigurationStatusData = async () => {
      try {
        const response = await axios.get('http://localhost:8000/ready');
        const responseData = response.data;
        setApiReadyResponse(responseData);
        console.log(responseData);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    // Call the fetctConfigurationStatusData function when the component mounts
    fetctConfigurationStatusData();
  }, [isHueModalOpen, isSpotifyModalOpen]); 

  //apiReadyResponse.data.hue_ready and apiReadyResponse.data.spotify_ready
  return (
    <div className="app">
      <div className="app-container"> 
      {apiReadyResponse &&     
        <ButtonContainer>
          <PrimaryButton text="configure hue" fontSize="40px" disabled={apiReadyResponse.data.hue_ready} onClick={openHueModal}/>
          <PrimaryButton text="configure spotify" fontSize="40px" disabled={apiReadyResponse.data.spotify_ready} onClick={openSpotifyModal}/>
        </ButtonContainer>}
      {isHueModalOpen &&
          <HueConfigureModal isOpen={isHueModalOpen} onClose={closeHueModal} apiEndpoint="http://localhost:8000/setup-hue"/>
      }
      {isSpotifyModalOpen &&
          <SpotifyConfigureModal isOpen={isSpotifyModalOpen} onClose={closeSpotifyModal} apiEndpoint="http://localhost:8000/authorize-spotify"/>
      }
      </div>
    </div>
  );
}

export default App;
