
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AutonomousActionHub} from "src/AutonomousActionHub.sol";

contract YieldMindController is AutonomousActionHub {
    constructor(
        address admin,
        address operator,
        address reporter,
        uint256 initialPrincipalFloor
    ) AutonomousActionHub(admin, operator, reporter, initialPrincipalFloor) {}
}
