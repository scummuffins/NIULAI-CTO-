// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/common/ERC2981.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title NiulaiV2
 * @notice Relaunch contract for the 999-piece 牛来 (NIULAI) collection on BNB Smart Chain.
 *
 * Differences from the original contract, all deliberate:
 *  - `tokenURI` is built from an ipfs:// base URI, not a single centralised gateway domain.
 *    The original pointed at https://niulai.sbs/... , so one expired pin plus one parked
 *    domain was enough to break all 999 tokens.
 *  - The royalty receiver is changeable (the original hard-coded it with no setter).
 *  - `freezeMetadata()` lets you give up baseURI control once the art is pinned and stable,
 *    so holders get a permanent guarantee it can never be swapped or rugged again.
 *
 * Token ids are 1..999 and `tokenURI(id)` resolves to `<baseURI><id>.json`, matching the
 * recovered metadata layout in ../metadata_rehost/.
 */
contract NiulaiV2 is ERC721, ERC2981, Ownable {
    using Strings for uint256;

    uint256 public constant MAX_SUPPLY = 999;

    string private _base;
    bool public metadataFrozen;
    uint256 public totalMinted;

    event BaseURIUpdated(string baseURI);
    event MetadataFrozen();

    /**
     * @param baseURI_        e.g. "ipfs://bafy.../"  — MUST include the trailing slash
     * @param royaltyReceiver address that receives secondary royalties
     * @param royaltyBps      royalty in basis points (1000 = 10%, matching the original)
     */
    constructor(string memory baseURI_, address royaltyReceiver, uint96 royaltyBps)
        ERC721(unicode"牛来 NFT", "NIULAI")
        Ownable(msg.sender)
    {
        _base = baseURI_;
        _setDefaultRoyalty(royaltyReceiver, royaltyBps);
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

    // ------------------------------------------------------------------ royalties

    function setDefaultRoyalty(address receiver, uint96 feeBps) external onlyOwner {
        _setDefaultRoyalty(receiver, feeBps);
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
        public view override(ERC721, ERC2981) returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
