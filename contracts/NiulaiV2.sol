// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/interfaces/IERC2981.sol";
import "@openzeppelin/contracts/utils/introspection/IERC165.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title NiulaiV2
 * @notice Relaunch contract for the 999-piece 牛来 (NIULAI) collection on BNB Smart Chain.
 *
 * ZERO ROYALTY, PERMANENTLY.
 * `royaltyInfo` is a hardcoded `pure` function returning `(address(0), 0)`. There is no royalty
 * storage, no setter, and no owner-only escape hatch anywhere in this contract - not even an
 * internal one. Because the function is `pure` it cannot read state, so it can never return
 * anything else for any token at any price, and no future transaction can alter that. Verify it
 * yourself after deployment by calling `royaltyInfo(1, 10000)` on BscScan.
 *
 * The contract still declares EIP-2981 support deliberately. Marketplaces that query it read an
 * explicit on-chain zero; a contract that omitted EIP-2981 entirely would leave them falling back
 * to their own configurable defaults instead.
 *
 * Other differences from the original contract, all deliberate:
 *  - `tokenURI` is built from an ipfs:// base URI, not a single centralised gateway domain. The
 *    original pointed at https://niulai.sbs/... , so one expired pin plus one parked domain was
 *    enough to break all 999 tokens at once.
 *  - `freezeMetadata()` lets the owner permanently give up the ability to change the artwork once
 *    it is pinned and stable.
 *
 * Token ids are 1..999 and `tokenURI(id)` resolves to `<baseURI><id>.json`, matching the
 * recovered metadata layout in ../metadata_rehost/.
 */
contract NiulaiV2 is ERC721, IERC2981, Ownable {
    using Strings for uint256;

    uint256 public constant MAX_SUPPLY = 999;

    string private _base;
    bool public metadataFrozen;
    uint256 public totalMinted;

    event BaseURIUpdated(string baseURI);
    event MetadataFrozen();

    /**
     * @param baseURI_ e.g. "ipfs://bafy.../" - MUST include the trailing slash.
     *                 There are no royalty parameters: the royalty is fixed at zero in code.
     */
    constructor(string memory baseURI_)
        ERC721(unicode"牛来 NFT", "NIULAI")
        Ownable(msg.sender)
    {
        _base = baseURI_;
    }

    // ------------------------------------------------------------------ royalties

    /**
     * @notice Always zero. Hardcoded and `pure` - it reads no state and there is no setter,
     *         so this return value is fixed for the life of the contract.
     */
    function royaltyInfo(uint256, uint256) external pure override returns (address, uint256) {
        return (address(0), 0);
    }

    // ------------------------------------------------------------------ metadata

    function _baseURI() internal view override returns (string memory) {
        return _base;
    }

    /// @dev appends ".json" so ids map onto 1.json .. 999.json
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        return string(abi.encodePacked(_base, tokenId.toString(), ".json"));
    }

    function setBaseURI(string calldata baseURI_) external onlyOwner {
        require(!metadataFrozen, "NiulaiV2: metadata frozen");
        _base = baseURI_;
        emit BaseURIUpdated(baseURI_);
    }

    /// @notice One-way. After this, the artwork can never be changed by anyone.
    function freezeMetadata() external onlyOwner {
        metadataFrozen = true;
        emit MetadataFrozen();
    }

    // ------------------------------------------------------------------ distribution

    /**
     * @notice Mint recovered token ids directly to their current holders.
     * @dev Call in batches (~100 per tx) to stay well inside the block gas limit.
     *      Arrays are index-aligned: recipients[i] receives tokenIds[i].
     */
    function airdrop(address[] calldata recipients, uint256[] calldata tokenIds) external onlyOwner {
        require(recipients.length == tokenIds.length, "NiulaiV2: length mismatch");
        for (uint256 i; i < recipients.length; ++i) {
            uint256 id = tokenIds[i];
            require(id >= 1 && id <= MAX_SUPPLY, "NiulaiV2: id out of range");
            _safeMint(recipients[i], id);
            unchecked { ++totalMinted; }
        }
    }

    function totalSupply() external view returns (uint256) {
        return totalMinted;
    }

    // ------------------------------------------------------------------ plumbing

    function supportsInterface(bytes4 interfaceId)
        public view override(ERC721, IERC165) returns (bool)
    {
        return interfaceId == type(IERC2981).interfaceId || super.supportsInterface(interfaceId);
    }
}
