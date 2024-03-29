import './App.css';
import axios from 'axios';
import React, { useState, useEffect } from 'react';
import ButtonContainer from './components/ButtonContainer';
import HueConfigureModal from './components/HueConfigureModal';
import SpotifyConfigureModal from './components/SpotifyConfigureModal';
import PrimaryButton from './components/PrimaryButton';
import SelectLightsContainer from './containers/SelectLightsContainer';

function App() {
  const [apiReadyResponse, setApiReadyResponse] = useState(null);
  const [isHueModalOpen, setIsHueModalOpen] = useState(false);
  const [isSpotifyModalOpen, setIsSpotifyModalOpen] = useState(false);
  const [areBothConfigurationsReady, setAreBothConfigurationsReady] = useState(false);

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
    const fetchConfigurationStatusData = async () => {
      try {
        const response = await axios.get('http://localhost:8000/ready');
        const responseData = response.data;
        setApiReadyResponse(responseData);

        if (responseData.data.hue_ready && responseData.data.spotify_ready) {
          setAreBothConfigurationsReady(true);
        } else {
          setAreBothConfigurationsReady(false);
        }

        console.log(responseData);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    // Call the fetchConfigurationStatusData function when the component mounts
    fetchConfigurationStatusData();
  }, [isHueModalOpen, isSpotifyModalOpen]); 

  //apiReadyResponse.data.hue_ready and apiReadyResponse.data.spotify_ready
  return (
    <div className="app">
      <div className="app-container">
      {apiReadyResponse &&     
         <ButtonContainer>
         {!areBothConfigurationsReady && (
           <>
             <PrimaryButton
               text={apiReadyResponse.data.hue_ready ? "hue configured" : "configure hue"}
               fontSize="40px"
               disabled={apiReadyResponse.data.hue_ready}
               onClick={openHueModal}
             />
             <PrimaryButton
               text={apiReadyResponse.data.spotify_ready ? "spotify configured" : "configure spotify"}
               fontSize="40px"
               disabled={apiReadyResponse.data.spotify_ready}
               onClick={openSpotifyModal}
             />
           </>
         )}
       </ButtonContainer>
      }

      {areBothConfigurationsReady && (
          <SelectLightsContainer/>
         )}

      {isHueModalOpen &&
          <HueConfigureModal isOpen={isHueModalOpen} onClose={closeHueModal}
          apiEndpoint="http://localhost:8000/setup-hue"/>
      }

      {isSpotifyModalOpen &&
          <SpotifyConfigureModal isOpen={isSpotifyModalOpen} onClose={closeSpotifyModal}
          apiEndpoint="http://localhost:8000/authorize-spotify"/>
      }
      </div>
    </div>
  );
}

export default App;
