// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AutonomousActionCore} from "src/AutonomousActionCore.sol";

contract AutonomousActionHub is AutonomousActionCore {
    struct Profile {
        address operator;
        bytes32 manifestHash;
        bytes32 metadataHash;
        uint96 reputation;
        bool active;
        uint64 updatedAt;
    }

    struct QueuedTask {
        address target;
        bytes4 selector;
        uint128 amount;
        bytes32 evidenceHash;
        uint64 queuedAt;
        bool executed;
    }

    uint256 public principalFloor;
    mapping(bytes32 => Profile) public profiles;
    mapping(bytes32 => QueuedTask) public queuedTasks;

    error PrincipalFloorBreached(uint256 liquidBalance, uint256 principalFloor, uint256 requestedAmount);
    error ProfileMissing(bytes32 subjectId);
    error UnknownTask(bytes32 actionId);
    error TaskAlreadyExecuted(bytes32 actionId);

    constructor(
        address admin,
        address operator,
        address reporter,
        uint256 initialPrincipalFloor
    ) AutonomousActionCore(admin, operator, reporter) {
        principalFloor = initialPrincipalFloor;
    }

    function setPrincipalFloor(uint256 newPrincipalFloor)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        principalFloor = newPrincipalFloor;
    }

    function spendableBuffer(uint256 liquidBalance) public view returns (uint256) {
        return liquidBalance > principalFloor ? liquidBalance - principalFloor : 0;
    }

    function executeBoundedAction(
        bytes32 actionId,
        address target,
        bytes4 selector,
        uint256 amount,
        uint256 liquidBalance,
        bytes32 callHash
    ) external onlyRole(OPERATOR_ROLE) whenNotPaused nonReentrant returns (bytes32) {
        if (amount > spendableBuffer(liquidBalance)) {
            revert PrincipalFloorBreached(liquidBalance, principalFloor, amount);
        }
        _consumePolicy(actionId, amount);
        _enforceTargetAndSelector(target, selector);
        bytes32 digest = keccak256(
            abi.encode(actionId, target, selector, amount, liquidBalance, callHash)
        );
        executionDigests[actionId] = digest;
        return digest;
    }

    function registerProfile(
        bytes32 subjectId,
        address operatorAddress,
        bytes32 manifestHash,
        bytes32 metadataHash
    ) external onlyRole(REPORTER_ROLE) whenNotPaused {
        profiles[subjectId] = Profile({
            operator: operatorAddress,
            manifestHash: manifestHash,
            metadataHash: metadataHash,
            reputation: 0,
            active: true,
            updatedAt: uint64(block.timestamp)
        });
    }

    function updateReputation(
        bytes32 subjectId,
        uint96 newReputation,
        bytes32 evidenceHash
    ) external onlyRole(REPORTER_ROLE) whenNotPaused {
        Profile storage profile = profiles[subjectId];
        if (profile.updatedAt == 0) {
            revert ProfileMissing(subjectId);
        }
        profile.reputation = newReputation;
        profile.updatedAt = uint64(block.timestamp);
        executionDigests[subjectId] = evidenceHash;
    }

    function attachProof(bytes32 subjectId, bytes32 proofDigest)
        external
        onlyRole(REPORTER_ROLE)
        whenNotPaused
    {
        Profile storage profile = profiles[subjectId];
        if (profile.updatedAt == 0) {
            revert ProfileMissing(subjectId);
        }
        receiptDigests[subjectId] = proofDigest;
        profile.updatedAt = uint64(block.timestamp);
    }

    function queueTask(
        bytes32 actionId,
        address target,
        bytes4 selector,
        uint128 amount,
        bytes32 evidenceHash
    ) external onlyRole(REPORTER_ROLE) whenNotPaused {
        queuedTasks[actionId] = QueuedTask({
            target: target,
            selector: selector,
            amount: amount,
            evidenceHash: evidenceHash,
            queuedAt: uint64(block.timestamp),
            executed: false
        });
    }

    function executeQueuedTask(bytes32 actionId, bytes32 callHash)
        external
        onlyRole(OPERATOR_ROLE)
        whenNotPaused
        nonReentrant
        returns (bytes32)
    {
        QueuedTask storage task = queuedTasks[actionId];
        if (task.queuedAt == 0) {
            revert UnknownTask(actionId);
        }
        if (task.executed) {
            revert TaskAlreadyExecuted(actionId);
        }
        _consumePolicy(actionId, task.amount);
        _enforceTargetAndSelector(task.target, task.selector);
        task.executed = true;
        bytes32 digest = keccak256(
            abi.encode(actionId, task.target, task.selector, task.amount, callHash)
        );
        executionDigests[actionId] = digest;
        return digest;
    }
}
