import React, { useState, FC, useRef, useEffect, ReactNode, useContext } from 'react';
import { ServerAPI, MenuItem, Menu } from 'decky-frontend-lib';
import { ModalContext } from './ModalContext';

interface IUserMenuProps {
    userID: number;
    userName: string;
  }

export const UserMenu: FC<IUserMenuProps> = ({ userID, userName }) => {
    const modalContext = useContext(ModalContext);
    if (!modalContext) {
      throw new Error("UserMenu must be used within a ModalContext.Provider");
    }
    const { handleOpenModal, setSelectedRecipient } = modalContext;

    return (
      <Menu label={userName}>
        <MenuItem onClick={() => console.log(`Mute user: ${userName}`)}>
          Local Mute
        </MenuItem>
        <MenuItem
          onClick={() => {
            setSelectedRecipient({ ID: userID, name: userName });
            handleOpenModal();
          }}
        >
          Send Message
        </MenuItem>
        <MenuItem onClick={() => console.log(`Kick user: ${userName}`)}>
          Kick
        </MenuItem>
      </Menu>
    );
  };